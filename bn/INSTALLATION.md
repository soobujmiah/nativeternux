# Native Termux ইনস্টল নির্দেশিকা

Ternuxx Native Termux প্যাকেজ preview-first পরিকল্পনায় ইনস্টল করে। এটি Linux guest তৈরি বা পরিচালনা করে না।

## ইনস্টল

Termux-এ X11 package repository চালু করে Git ইনস্টল করুন, তারপর Ternuxx clone করে প্যাকেজ পরিকল্পনা দেখুন:

```sh
pkg update && pkg install x11-repo git && pkg update
git clone https://github.com/soobujmiah/ternuxx.git "$HOME/ternuxx"
cd "$HOME/ternuxx"
./tx install preview
```

প্যাকেজ ও dependency পরিবর্তন পর্যালোচনা করে শুধু সংরক্ষিত পরিকল্পনার ID দিয়ে apply করুন:

```sh
./tx install apply PLAN_ID
```

এই পরিকল্পনা package remove বা upgrade করে না। Ternuxx core আপগ্রেড দেখতে:

```sh
./tx install update preview
./tx install update apply PLAN_ID
```

আপডেট পরিকল্পনা package remove, downgrade বা অফিসিয়াল Termux repository-এর বাইরের পরিবর্তন প্রত্যাখ্যান করে। ডেস্কটপের জন্য Android-এ মেলে এমন Termux:X11 অ্যাপ আলাদাভাবে ইনস্টল করতে হবে।

## প্রথম পরীক্ষা ও ডেস্কটপ

```sh
./tx help
./tx guides
./tx doctor
./tx info
```

Android-এ Termux:X11 অ্যাপ খুলে Native ডেস্কটপ চালু করুন:

```sh
./tx start
```

Interactive ব্যবস্থাপনার জন্য `./tx tui`, `./tx web`, অথবা `./tx mng center` ব্যবহার করুন। কোন action পাওয়া যাবে তা client ভেদে আলাদা হতে পারে। [সক্ষমতার তালিকা](../docs/architecture/CAPABILITY-MATRIX.md) দেখুন।

## SSH ও recovery

`./tx ssh inspect` Native SSH অবস্থা দেখায়। Managed SSH lifecycle action-এ preview ও confirmation লাগে। Ternuxx-এর managed service loopback port 8023-এ চলে; port 8022 আলাদা মালিক-পরিচালিত development channel।

`./tx backup`, `./tx recovery` এবং `./tx checkpoint` Native state backup ও recovery-র নির্দেশনা দেয়। পরিবর্তনের আগে লক্ষ্য ও পরিকল্পনা দেখে নিন। Ternuxx shared storage scan করে না বা নির্বিচারে ফাইল পরিচালনা করে না।

## সীমাবদ্ধতা

বর্তমান ডিভাইস আগে থেকেই কনফিগার করা; এটি নতুন ডিভাইসে পুনরুৎপাদনের প্রমাণ নয়। Package version বদলাতে পারে, আর সংরক্ষিত preview offline mirror নয়। GPU/NPU acceleration, rollback, ডিভাইস সমর্থন এবং public release-এর জন্য আলাদা প্রমাণ দরকার।

## ঐচ্ছিক Native অ্যাপ

আলাদা curated catalog-এ htop, tmux এবং tree আছে। `tx app list` দিয়ে দেখুন, তারপর নির্দিষ্ট install plan preview করে apply করুন। tree ইনস্টল থাকলে `tx app run directory-tree HOME_PATH` Native HOME-এর path সীমিত ও read-only ভাবে তালিকাভুক্ত করে। এটি shared storage বা ফাইলের content পড়ে না। বিস্তারিত: [software catalog](../docs/SOFTWARE-CATALOG.md)।
