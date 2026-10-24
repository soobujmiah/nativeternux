# Ternuxx

Ternuxx হলো Android-এর Native Termux-এর জন্য ওয়ার্কস্টেশন ম্যানেজার। `tx` দিয়ে Termux:X11 ডেস্কটপ, Native সার্ভিস, SSH, স্বাস্থ্য পরীক্ষা, ব্যাকআপ ও recovery পরিচালনা করা যায়। CLI, TUI, Web এবং GTK ইন্টারফেস একই Native Termux পরিবেশে কাজ করে।

২০২৬-১০-২৪ তারিখে মালিক Ternuxx-কে Native Termux-only করেছেন। PRoot guest support বন্ধ, ইনস্টল করা ছয়টি guest সরানো এবং `proot` ও `proot-distro` প্যাকেজ uninstall করা হয়েছে। পুরোনো রিপোর্টগুলো তারিখসহ historical record হিসেবে রাখা হয়েছে; সেগুলো বর্তমান সমর্থিত আচরণ বোঝায় না। বিস্তারিত [migration audit](../docs/evidence/2026-10-24-native-only-proot-removal-audit.md), [বর্তমান অবস্থা](../CURRENT_STATE.md) এবং [সিদ্ধান্ত ADR-0017](../docs/architecture/decisions/ADR-0017-native-only-product-and-proot-retirement.md)-তে।

## শুরু করুন

```sh
./tx help
./tx guides
./tx doctor
./tx install preview
```

প্যাকেজ পরিবর্তনের আগে পূর্বরূপের নির্দিষ্ট পরিকল্পনা পর্যালোচনা করুন। ডেস্কটপের জন্য Android-এ উপযুক্ত Termux:X11 অ্যাপ আলাদাভাবে লাগবে। বিস্তারিত [ইনস্টল নির্দেশিকা](INSTALLATION.md) ও [অপারেশন গাইড](../docs/OPERATIONS.md)-এ।

## স্থানীয় CPU মডেল

`./tx ai status` দিয়ে Termux-এর `llama-cpp` runtime ও Ternuxx-এর নির্দিষ্ট model পরীক্ষা করুন। Runtime না থাকলে আগে `apt-get -s install llama-cpp` দিয়ে package পরিবর্তনের পূর্বরূপ দেখুন; Ternuxx নিজে package install করে না। Runtime থাকলে `./tx ai setup` model download-এর পূর্বরূপ দেখায়; ডাউনলোডের আগে `DOWNLOAD` লিখে নিশ্চিত করতে হয়। Model-এর নির্দিষ্ট আকার ও SHA-256 যাচাই হওয়ার পরই সেটি private Ternuxx state-এ রাখা হয়।

`./tx ai run` টার্মিনাল বা stdin থেকে এক লাইনের prompt নেয় এবং CPU-তেই সীমাবদ্ধ run করে। Model নামাতে network লাগে; model ফাইল local-এ থাকলে inference-এর জন্য network লাগে না। বিস্তারিত [CPU baseline](../docs/testing/CPU-BASELINE.md) ও [workflow evidence](../docs/evidence/2026-10-24-native-cpu-inference-workflow.md)-এ।

## ইন্টারফেস

- `./tx` — কমান্ড লাইন
- `./tx tui` — টার্মিনালের interactive ব্যবস্থাপনা
- `./tx web` — authenticated loopback Web UI
- `./tx gui` — চলমান Native ডেস্কটপের GTK management center

Ternuxx এখনো উন্নয়নাধীন। পরীক্ষায় উত্তীর্ণ হওয়া মানে সব Android ডিভাইস, GPU/NPU বা workload সমর্থিত—এমন নয়। প্রকল্পের লাইসেন্স এখনো নির্ধারিত হয়নি।

[স্থাপত্য](../docs/ARCHITECTURE.md) · [সক্ষমতার তালিকা](../docs/architecture/CAPABILITY-MATRIX.md) · [নিরাপত্তা](../SECURITY.md) · [সব নথি](../docs/README.md)
