# NativeTernux — বাংলা

**NativeTernux** হলো একটি Termux-নেটিভ ডেস্কটপ প্রজেক্ট। PRoot বা Debian container ছাড়াই, সরাসরি Termux-এর প্যাকেজ থেকে XFCE ডেস্কটপ চালানো যায়। কোনো root প্রয়োজন নেই।

## কী এটা?

[ternux](https://github.com/soobujmiah/ternux) থেকে ভিন্ন — এখানে PRoot + Debian বাদ। সব কিছু Termux-এর নিজস্ব প্যাকেজ রিপোজিটরি থেকে চলে:

- **XFCE4 ডেস্কটপ** — `termux-x11` রিপো থেকে
- **Chromium ব্রাউজার** — `termux-x11` রিপো থেকে
- **GPU এক্সিলারেশন** — Mesa Zink + Turnip (Adreno Vulkan ড্রাইভার ইতিমধ্যে Termux-এ আছে)
- **PulseAudio** — সাউন্ডের জন্য (ইতিমধ্যে ইনস্টল করা আছে)
- **Termux:X11** — ডিসপ্লে সার্ভার হিসেবে

## বর্তমান অবস্থা: মাইলস্টোন ১ — স্কাফোল্ড

| আইটেম | অবস্থা |
|--------|--------|
| CLI skeleton | ✅ সম্পন্ন |
| `check` কমান্ড | ✅ ইমপ্লিমেন্টেড |
| `info` কমান্ড | ✅ ইমপ্লিমেন্টেড |
| `doctor` কমান্ড | ✅ ইমপ্লিমেন্টেড |
| `help` / `guides` | ✅ ইমপ্লিমেন্টেড |
| প্যাকেজ ইনস্টলেশন | ⏳ মাইলস্টোন ২ (`--yes` কনসেন্ট লাগবে) |
| ডেস্কটপ লঞ্চ | ⏳ মাইলস্টোন ২ (প্যাকেজ লাগবে) |
| GPU বেনচমার্কিং | ⏳ মাইলস্টোন ৩ |
| হাইব্রিড মোড (Proot fallback) | ⏳ মাইলস্টোন ৪ |

## দ্রুত শুরু (মাইলস্টোন ২-এর পর)

```bash
# কী রেডি আছে দেখুন
nativeternux check

# সিস্টেম ইনফো
nativeternux info

# প্রয়োজনীয় প্যাকেজ ইনস্টল (একবার, --yes লাগবে)
nativeternux install --yes

# ডেস্কটপ চালু
nativeternux start

# বন্ধ
nativeternux stop
```

## আর্কিটেকচার

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design.

**Tier 1 — Native (বর্তমান ফোকাস):**
```
Android → Termux packages → XFCE4 + Chromium + Zink/Turnip → Termux:X11
```

**Tier 2 — Proot (ভবিষ্যত):** হালকা Debian container glibc-only টুলসের জন্য (blender, ffmpeg, dev toolchains)।

**Tier 3 — Hybrid (ভবিষ্যত):** স্মার্ট ডিসপ্যাচ — নেটিভ অ্যাপস Termux-এ, Linux-only অ্যাপস Proot-এ।

## লাইসেন্স

PolyForm Noncommercial 1.0.0 plus the Ternux commercial-use addendum.
See [LICENSE](LICENSE) and [LICENSE-SCOPE.md](LICENSE-SCOPE.md).

NativeTernux হলো [soobujmiah/ternux](https://github.com/soobujmiah/ternux) থেকে আলাদা প্রজেক্ট। উভয়ের একই লাইসেন্স কিন্তু আলাদা কোডবেস ও উদ্দেশ্য।

## রিপোজিটরি

- **সোর্স:** https://github.com/soobujmiah/nativeternux
- **ডক্স:** https://soobujmiah.github.io/nativeternux/ (ভবিষ্যতে)
- **ইস্যু:** https://github.com/soobujmiah/nativeternux/issues
