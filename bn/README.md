# Ternuxx — বাংলা

আমার phone-টাই pocket-er workstation হবে। Native Termux-er direct সুবিধা আর আমার Ternux PRoot-er Linux/GPU setup—দুটো একসাথে কাজে লাগাতে চাই। [আমার কথা](../docs/PRODUCT-VISION.md)। CPU baseline; GPU/NPU support actual workload-e verify korte hobe।

## GPU ও PRoot সম্পর্কে

এই ডিভাইসে native Termux-এর পরীক্ষিত Turnip package Adreno 825-কে `VK_ERROR_INCOMPATIBLE_DRIVER` দিয়ে প্রত্যাখ্যান করেছে। এই ফল শুধু পরীক্ষিত native package/process-এর জন্য প্রযোজ্য। Existing Ternux-এর Debian PRoot-এ আলাদা Zink/Turnip graphics path আছে—সেটি Ternuxx থেকে নিয়ন্ত্রিত বা পুনরায় যাচাই করা হয়নি। বিস্তারিত: [PRoot GPU reuse](../docs/PROOT-GPU.md) এবং [Research & Evidence](../docs/RESEARCH.md)।

Shader cache folder থাকা একা GPU renderer প্রমাণ করে না। চলমান desktop-এ `glxinfo -B` থেকে Zink/Turnip renderer দেখা দরকার; `llvmpipe` হলে সেটি software rendering।

Ternuxx কোনো অবস্থাতেই নিজে থেকে Ternux-এর `~/x.sh`, Debian rootfs, display/audio lifecycle বা cleanup পরিবর্তন/trim করবে না। ভবিষ্যৎ PRoot integration opt-in হবে, existing Ternux capability parity বজায় রাখবে এবং ownership-aware lifecycle না হওয়া পর্যন্ত আলাদা Ternuxx desktop একই display-তে চালানো হবে না। CPU baseline; GPU/NPU কেবল actual workload backend evidence থাকলেই supported বলা হবে।

## বর্তমান অবস্থা

| সক্ষমতা | অবস্থা |
|---|---|
| Read-only CLI scaffold | আছে |
| Native package installation | পরিকল্পিত; implement করা হয়নি |
| Native XFCE lifecycle | পরিকল্পিত; implement করা হয়নি |
| পরীক্ষিত Adreno 825-এ native Turnip | পর্যবেক্ষিত package-এ ব্যর্থ |
| Existing Ternux PRoot reuse | নকশা ও documentation আছে; adapter নেই |
| CPU/GPU/NPU capability verification | পরিকল্পিত; NPU access এখনো প্রমাণিত নয় |
| Hybrid workflow | ভবিষ্যৎ কাজ; Native ও PRoot-এর শক্তি safe handoff-এ একত্র করা |

আরও দেখুন: [আমার vision](../docs/PRODUCT-VISION.md), [Architecture](../docs/ARCHITECTURE.md), [Roadmap](../docs/ROADMAP.md), [Installation status](../docs/INSTALLATION.md)।

## লাইসেন্স

এই repository-তে license এখনো নির্ধারিত/যোগ করা হয়নি। আগের draft-এর license দাবি ও অনুপস্থিত license file-এর link-কে কার্যকর license হিসেবে ধরবেন না। Public release বা contribution নেওয়ার আগে owner-কে license নির্বাচন করে file যোগ করতে হবে।

## Repository

- Source: https://github.com/soobujmiah/ternuxx
- Existing Ternux (independent): https://github.com/soobujmiah/ternux
