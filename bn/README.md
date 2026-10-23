# Ternuxx — বাংলা

আমার phone-টাই pocket-er workstation হবে। Native Termux-er direct সুবিধা আর আমার Ternux PRoot-er Linux/GPU setup—দুটো একসাথে কাজে লাগাতে চাই। [আমার কথা](../docs/PRODUCT-VISION.md)। CPU baseline; GPU/NPU support actual workload-e verify korte hobe।

## GPU ও PRoot সম্পর্কে

Native Termux ও Debian PRoot আলাদা graphics provider; একটির ফল অন্যটির GPU support প্রমাণ করে না। Ternuxx-এর PRoot graphics check ও সীমা দেখুন [PRoot GPU reuse](../docs/PROOT-GPU.md) এবং [Research & Evidence](../docs/RESEARCH.md)-এ। তারিখযুক্ত GPU ফলকে বর্তমান package/version-এর নিশ্চয়তা ধরে নেবেন না।

Shader cache folder থাকা একা GPU renderer প্রমাণ করে না। চলমান desktop-এ `glxinfo -B` থেকে Zink/Turnip renderer দেখা দরকার; `llvmpipe` হলে সেটি software rendering।

Ternuxx এখন Native Termux থেকে PRoot-Distro Debian-কে নিজস্ব typed adapter দিয়ে inspect ও পরিচালনা করে; আলাদা Ternux CLI runtime dependency নয়। প্রয়োজনীয় guest package/config পরিবর্তন কেবল নির্দিষ্ট guest, exact preview, explicit apply ও rollback সহ করতে হবে; rootfs reset/replace বা অচিহ্নিত cleanup নয়। একই display-তে desktop lifecycle চালাতে owner যাচাই দরকার। CPU baseline; GPU/NPU support actual workload evidence ছাড়া দাবি করা যাবে না।

## বর্তমান অবস্থা

| সক্ষমতা | অবস্থা |
|---|---|
| Native package ও desktop lifecycle | Implemented; বর্তমান parity/acceptance [phase status](../docs/PHASE-STATUS.md)-এ দেখুন |
| পরীক্ষিত Adreno 825-এ native Turnip | পর্যবেক্ষিত package-এ ব্যর্থ |
| Debian PRoot integration | Ternuxx-এর typed provider/management operations আছে; P4 feature parity ও acceptance চলমান |
| CPU/GPU/NPU capability verification | পরিকল্পিত; NPU access এখনো প্রমাণিত নয় |
| Hybrid workflow | CLI/TUI/Web/GTK-তে অনেক shared lifecycle ও handoff আছে; অসম্পূর্ণ parity ও reproducibility audit চলমান |

আরও দেখুন: [আমার vision](../docs/PRODUCT-VISION.md), [Architecture](../docs/ARCHITECTURE.md), [Roadmap](../docs/ROADMAP.md), [Installation status](../docs/INSTALLATION.md)।

## লাইসেন্স

এই repository-তে license এখনো নির্ধারিত/যোগ করা হয়নি। আগের draft-এর license দাবি ও অনুপস্থিত license file-এর link-কে কার্যকর license হিসেবে ধরবেন না। Public release বা contribution নেওয়ার আগে owner-কে license নির্বাচন করে file যোগ করতে হবে।

## Repository

- Source: https://github.com/soobujmiah/ternuxx
- Existing Ternux (independent): https://github.com/soobujmiah/ternux
