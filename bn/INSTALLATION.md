# Ternuxx ইনস্টল ও ব্যবহার নির্দেশিকা

এই পাতায় Termux প্রস্তুত করা থেকে Native Ternuxx চালানো এবং আলাদা Debian PRoot পরিবেশ তৈরি করা পর্যন্ত ধাপগুলো দেওয়া হয়েছে। ইংরেজি বিস্তারিতের জন্য [ইনস্টল নির্দেশিকা](../docs/INSTALLATION.md) দেখুন।

## ১. প্রয়োজনীয় জিনিস

- Android-এ Termux ইনস্টল করুন এবং একই উৎস থেকে এর প্যাকেজ ব্যবস্থাপনা ব্যবহার করুন।
- ডেস্কটপ লাগলে Android-এর উপযোগী **Termux:X11 অ্যাপ** ইনস্টল করুন। Android অ্যাপটি Termux-এর প্যাকেজ থেকে আলাদা।
- পর্যাপ্ত খালি জায়গা ও নির্ভরযোগ্য ইন্টারনেট সংযোগ রাখুন। Debian পরিবেশের জন্য Native ইনস্টল-এর চেয়ে অনেক বেশি জায়গা লাগতে পারে।
- কোনো পুরোনো Debian পরিবেশ থাকলে তার alias লিখে রাখুন। নিচের নতুন-অতিথি তৈরির ধাপে সেটি লক্ষ্য করবেন না।

## ২. Ternuxx নামান এবং ইনস্টল পরিকল্পনা দেখুন

```sh
pkg update
pkg install x11-repo git
pkg update
git clone https://github.com/soobujmiah/ternuxx.git "$HOME/ternuxx"
cd "$HOME/ternuxx"
./tx install --preview
```

পূর্বরূপে প্যাকেজের তালিকা, নির্ভরতা, সংস্করণ এবং পরিবর্তনের সারাংশ পড়ুন। পূর্বরূপ কোনো প্যাকেজ ইনস্টল করে না। Ternuxx-এর Native লেনদেন প্যাকেজ সরায় বা আপগ্রেড করে না এবং Debian rootfs তৈরি করে না।

## ৩. শুধু পর্যালোচিত পরিকল্পনা প্রয়োগ করুন

পূর্বরূপে দেখানো পরিকল্পনার আসল ID বসান:

```sh
./tx install --yes --plan-id PLAN_ID
```

নতুন পূর্বরূপ তৈরি হলে পুরোনো ID ব্যবহার করবেন না। ইনস্টলের পর:

```sh
./tx doctor
./tx info
./tx help
```

ডেস্কটপ চালু করতে Termux:X11 Android অ্যাপ খুলুন, তারপর প্রকল্পের ফোল্ডার থেকে চালান:

```sh
./tx start
```

বন্ধ, অবস্থা, বা পুনরায় চালুর কমান্ড জানতে `./tx help` দেখুন। ব্যবস্থাপনা ইন্টারফেস:

```sh
./tx tui
./tx web
./tx mng center
```

সব কাজ সব ইন্টারফেসে নেই; [সক্ষমতার তালিকা](../docs/architecture/CAPABILITY-MATRIX.md) দেখুন।

## ৪. বিদ্যমান Debian পরিবেশ থাকলে

প্রথমে অবস্থা দেখুন:

```sh
./tx proot setup status
```

বিদ্যমান working Debian guest-কে আরেকটি rootfs না বানিয়ে Ternuxx-এর Native profile-এ যুক্ত করতে:

```sh
./tx install debian
```

এটি read-only পূর্বরূপ দেখায়: Debian সংস্করণ, account, rootfs পরিচয়, manifest-এর প্রতিটি package group-এর install/hold অবস্থা, Ternuxx-এর নির্দিষ্ট graphics ফাইল এবং অন্য ICD config আলাদা করে। Guest dpkg database শুধু পড়া হয়; guest-এ login বা পরিবর্তন হয় না। Preview-তে blocker না থাকলেই plan apply করুন:

```sh
./tx install debian apply PLAN_ID --yes
```

এই প্রথম integration ধাপ Native পাশে ব্যক্তিগত profile record তৈরি করে; guest-এর ফাইল, package বা service বদলায় না এবং অনুপস্থিত package ইনস্টলও করে না। একই rootfs-এর পুরোনো adoption record হলে preview metadata refresh দেখাবে; apply-এর আগে আগের record-এর exact bytes backup হবে। অন্য rootfs-এর record থাকলে apply বন্ধ থাকবে। Apply ফলের backup ID দিয়ে tx proot setup adoption-rollback-preview --backup-id BACKUP_ID দেখুন; exact plan যাচাই করে tx proot setup adoption-rollback --backup-id BACKUP_ID --yes --plan-id PLAN_ID চালালে আগের record ফিরবে। account নির্দিষ্ট করতে `--user YOUR_DEBIAN_USERNAME` দিন। নিচের low-level command-গুলো একই adoption প্রক্রিয়ার পুরোনো রূপ.
## ৫. বিদ্যমান Debian না ছুঁয়ে নতুন অতিথি পরিবেশ পরীক্ষা করুন

আপনার আগে থেকেই Debian থাকলে নতুন পরীক্ষার জন্য অনন্য `ternuxx-replay-NAME` alias ব্যবহার করুন। `NAME`-এর জায়গায় ছোট ইংরেজি অক্ষর/সংখ্যা দিন; উদাহরণে `demo` ব্যবহার হয়েছে:

```sh
./tx proot setup fresh-preview --user YOUR_DEBIAN_USERNAME --alias ternuxx-replay-demo
```

পূর্বরূপে Debian image, তারিখ-নির্দিষ্ট snapshot, প্যাকেজের দল, খালি জায়গা, ব্যবহারকারী, গ্রাফিক্স-সংক্রান্ত সিদ্ধান্ত, লক্ষ্য alias এবং পরিকল্পনা ID—সবগুলো বিষয় যাচাই করুন। পূর্বনির্ধারিতভাবে manifest-এ থাকা সব প্যাকেজ নেওয়া হয়; কম প্যাকেজ চাইলে `--groups base,fonts` দিন। `base` দলটি আবশ্যক।

শুধু সঠিক পূর্বরূপ ID নিয়ে ইনস্টল করুন:

```sh
./tx proot setup fresh-install --user YOUR_DEBIAN_USERNAME --alias ternuxx-replay-demo --yes --plan-id PLAN_ID
```

ইনস্টল প্রয়োগের সময় নির্বাচিত guest ব্যবহারকারীর sudo password দুইবার গোপনে দিতে হবে। password শুধু stdin দিয়ে guest-এ পাঠানো হয়; command, preview, receipt বা log-এ রাখা হয় না। Native Termux বিদ্যমান Termux/Android app identity ব্যবহার করে; আলাদা Linux user বা sudo password তৈরি করে না। user ও password তৈরির এই ব্যবস্থা আপাতত শুধু fresh Debian Trixie provisioning-এ আছে। proot-distro-র অন্য distribution-গুলো এখনো Ternuxx দিয়ে provision করা যায় না। এতে আলাদা Debian কনটেইনারে প্যাকেজ ইনস্টল হবে; এটি সময় নিতে এবং অনেক জায়গা ব্যবহার করতে পারে। আগের `debian` পরিবেশ প্রতিস্থাপন করার কমান্ড নয়। নিজের ডিভাইস-এর পরিকল্পনা না বুঝলে প্রয়োগ করবেন না। ইনস্টল শেষে:

```sh
./tx proot status --json
```

তারপর আলাদা পরিবেশে প্রবেশ করতে:

```sh
./tx db --distro ternuxx-replay-demo
```

অতিথি পরিবেশের shell-এর কমান্ড আপনার সংস্করণে ভিন্ন হলে `./tx help` দেখুন। পরীক্ষা শেষ হলে এখনই container মুছবেন না—আগে retire/restore নীতি, ব্যাকআপ এবং নির্দিষ্ট পূর্বরূপ বুঝে নিন।

## ৬. ব্যর্থ নতুন পরিবেশ তৈরি আবার চালান

কোনো প্যাকেজ ধাপ ব্যর্থ হলে একই ব্যর্থ পরিকল্পনা সরাসরি প্রয়োগ করবেন না। ব্যর্থ পরিকল্পনার ID দিয়ে নতুন resume পূর্বরূপ বানান:

```sh
./tx proot setup fresh-resume-preview --user YOUR_DEBIAN_USERNAME --alias ternuxx-replay-demo --plan-id FAILED_PLAN_ID
./tx proot setup fresh-install --user YOUR_DEBIAN_USERNAME --alias ternuxx-replay-demo --yes --plan-id RESUME_PLAN_ID
```

Resume কেবল মিলে যাওয়া ব্যর্থ setup journal, একই নির্দিষ্ট image/snapshot/প্যাকেজ/গ্রাফিক্স profile, যাচাই করা rootfs পরিচয় এবং নিষ্ক্রিয় লক্ষ্য-এর জন্য অনুমোদিত হয়। পূর্বরূপে নতুন পরিকল্পনা ID মিলিয়ে তারপর চালান।

## গুরুত্বপূর্ণ সীমাবদ্ধতা

- Native প্যাকেজ সংস্করণ সময়ের সঙ্গে বদলাতে পারে। `tx install --preview` স্থায়ী সংস্করণ-লক নয়; বর্তমান পূর্বরূপ দেখেই সিদ্ধান্ত নিন। [সংস্করণ ভিন্নতার প্রমাণ](../docs/evidence/2026-10-23-native-package-version-drift.md) দেখুন।
- Fresh Debian replay আলাদা ডিভাইস, নতুন Android ব্যবস্থা, সব GUI অ্যাপ, Vulkan renderer বা অডিও পথ-এর যোগ্যতা যাচাই নয়।
- Ternuxx প্যাকেজ আপগ্রেড, Debian migration, ব্যাকআপ বা rollback সম্পর্কে নিশ্চিত না হলে সংশ্লিষ্ট কমান্ড চালাবেন না; আগে [ইংরেজি ইনস্টল নির্দেশিকা](../docs/INSTALLATION.md) ও [অপারেশন নির্দেশিকা](../docs/OPERATIONS.md) পড়ুন।
- প্রকল্পটি উন্নয়নাধীন; লাইসেন্স অনির্ধারিত। [প্রকাশনার প্রস্তুতি](../docs/readiness/README.md) দেখুন।

## সহায়তা ও রেফারেন্স

- [ইংরেজি দ্রুত শুরু](../README.md)
- [ইংরেজি ইনস্টল নির্দেশিকা](../docs/INSTALLATION.md)
- [কমান্ড তালিকা](../docs/OPERATIONS.md)
- [সক্ষমতার তালিকা](../docs/architecture/CAPABILITY-MATRIX.md)
- [পরিচিত সীমাবদ্ধতা](../docs/testing/KNOWN-LIMITATIONS.md)
