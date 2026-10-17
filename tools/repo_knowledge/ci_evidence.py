"""Read an actual same-repository CI run; never infer pass from collector setup."""
from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path

from . import cli


def status(conclusion):
    if conclusion == 'success':return 'passed'
    if conclusion in ('failure', 'timed_out', 'action_required', 'startup_failure'):return 'failed'
    return 'unknown'  # cancelled/skipped/unavailable are not executed test failures


def normalize_run_conclusion(conclusion):
    """Map raw GitHub Actions conclusion to canonical final-run status."""
    if conclusion == 'success':
        return 'passed'
    if conclusion in ('failure', 'action_required', 'startup_failure'):
        return 'failed'
    if conclusion in ('cancelled', 'skipped', 'timed_out'):
        return conclusion
    return 'unknown'


def derive(run, jobs, test_step):
    matches=[step for job in jobs for step in job.get('steps', []) if step.get('name') == test_step]
    if len(matches)>1:raise ValueError('ambiguous test step; use a unique workflow step name')
    step=matches[0] if matches else {}
    out = {'build_status':status(run.get('conclusion')), 'test_status':status(step.get('conclusion')),
           'build_at':run.get('updated_at'), 'test_at':step.get('completed_at') or run.get('updated_at'),
           'run_id':str(run['id']), 'run_attempt':str(run.get('run_attempt',1)),
           'source_commit':run['head_sha'], 'summary':f"{run.get('name', 'CI')}: {test_step}"}
    if run.get('conclusion') in ('success', 'failure', 'cancelled', 'skipped', 'timed_out', 'action_required', 'neutral', 'stale', 'startup_failure'):
        out['build_conclusion'] = run.get('conclusion')
    if step.get('conclusion') in ('success', 'failure', 'cancelled', 'skipped', 'timed_out', 'action_required', 'neutral', 'stale', 'startup_failure'):
        out['test_conclusion'] = step.get('conclusion')
    if run.get('name'):
        out['workflow_name'] = str(run['name'])
    if run.get('workflow_id') is not None:
        out['workflow_id'] = str(run['workflow_id'])
    if run.get('event'):
        out['event_type'] = str(run['event'])
    if run.get('run_started_at') or run.get('created_at'):
        out['started_at'] = run.get('run_started_at') or run.get('created_at')
    if run.get('updated_at'):
        out['completed_at'] = run.get('updated_at')
    actor = (run.get('actor') or {}).get('login') or (run.get('triggering_actor') or {}).get('login')
    if actor:
        out['actor'] = str(actor)
    if run.get('html_url'):
        out['run_url'] = str(run['html_url'])
    return out


def api(path, token):
    req=urllib.request.Request('https://api.github.com'+path,headers={
        'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','X-GitHub-Api-Version':'2022-11-28'})
    with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',default='.')
    p.add_argument('--run-id',required=True)
    p.add_argument('--workflow',required=True,help='expected workflow filename')
    p.add_argument('--branch',required=True)
    p.add_argument('--test-step',required=True)
    a=p.parse_args(argv)
    if not a.run_id.isdigit():raise SystemExit('run ID must be numeric')
    root=Path(a.root).resolve()
    import yaml
    repository=yaml.safe_load((root/'.repo/project.yaml').read_text())['repository']
    token=os.environ.get('GH_TOKEN') or os.environ.get('GITHUB_TOKEN')
    if not token:raise SystemExit('same-repository Actions-read token required')
    run=api(f'/repos/{repository}/actions/runs/{a.run_id}',token)
    head_repo=(run.get('head_repository') or {}).get('full_name') or (run.get('repository') or {}).get('full_name')
    if (run.get('status')!='completed' or run.get('event') not in ('push','schedule','workflow_dispatch','repository_dispatch') or
        run.get('head_branch')!=a.branch or head_repo!=repository or
        run.get('path','').split('@')[0]!='.github/workflows/'+a.workflow):
        raise SystemExit('run is not a completed trusted default-branch run of the configured workflow')
    jobs=[]
    for page in range(1,100):
        batch=api(f'/repos/{repository}/actions/runs/{a.run_id}/jobs?filter=latest&per_page=100&page={page}',token)['jobs']
        jobs.extend(batch)
        if len(batch)<100:break
    result=derive(run,jobs,a.test_step)
    args=['--root',str(root),'sync','--ci']
    for k in ['build_status','test_status','build_at','test_at','run_attempt','source_commit',
              'build_conclusion','test_conclusion','workflow_name','workflow_id','event_type',
              'started_at','completed_at','actor','run_url']:
        if result.get(k) is not None:args += ['--'+k.replace('_','-'),result[k]]
    args += ['--build-run-id',result['run_id'],'--test-run-id',result['run_id'],'--test-summary',result['summary']]
    return cli.main(args)

if __name__=='__main__':raise SystemExit(main())
