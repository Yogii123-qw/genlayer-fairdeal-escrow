# STATE.md - FairDeal Escrow (GenLayer Intelligent Contract)

## Status saat ini
- Fase: kode selesai, uji lokal LULUS 15/15, lint LULUS, review akhir Groq selesai dan temuan diperbaiki. Repo dibuat dan di-push (commit menyusul di bawah). Studio deploy BELUM dijalankan, butuh browser task induk.
- STOP SEBELUM SUBMIT ke Portal. Jangan pernah submit tanpa persetujuan Monch.

## Keputusan blueprint (dari NIM Nemotron + Groq, 20 Nov 2026)
- VERDICT keduanya: FIX FIRST. Temuan yang dipakai: escrow simetris (kedua pihak kunci dana sama besar), finalisasi tidak boleh mendahului banding (waive dua pihak atau banding sudah dipakai), batas panjang string, sanitasi klaim dengan json.dumps, validasi JSON sebelum tulis state, cek seller != buyer, status PAID ditulis sebelum transfer, jalur cancel bila seller tidak pernah mendanai.
- Temuan yang DITOLAK dengan bukti: (1) Groq bilang prompt_comparative mengembalikan Boolean. Salah. Template resmi wizard_of_coin.py memakai prompt_comparative lalu json.loads atas hasilnya. Dipakai. (2) Groq bilang TreeMap tidak boleh pakai Address sebagai key. Salah. Template resmi llm_erc20.py memakai TreeMap[Address, u256]. Desain ini memakai key u256 dan value Address, lebih aman lagi.
- Konsensus: gl.eq_principle.prompt_comparative, pola wizard_of_coin. Tanpa dataclass (@allow_storage tidak ada di bundle Studio v0.4.0), state memakai TreeMap paralel.

## Review akhir Groq atas kode final (20 Nov 2026)
- VERDICT: FIX FIRST, 3 temuan. Dua diperbaiki, satu ditolak dengan alasan:
- DIPERBAIKI 1: overflow amount * 2 di finalize. SDK membuktikan u256 adalah NewType atas int Python tanpa cek overflow, jadi cap stake 2**128 ditambah di create_deal. Cap ini jauh di atas stake nyata mana pun dan membuat payout tidak mungkin overflow.
- DIPERBAIKI 2: verdict pertama di appeal dikirim double-encoded (string JSON di-dumps lagi). Sekarang di-parse dulu dengan json.loads sebelum masuk prompt.
- DITOLAK: judge() terbuka untuk alamat mana pun. Alasan: verdict hanya ditentukan oleh dua klaim dan model, bukan oleh pemanggil. Waktu pemanggilan tidak mengubah input. Judge hanya bisa jalan sekali per deal, setelah itu status JUDGED menolak panggilan ulang. Pola yang sama berlaku untuk finalize publik. Membatasi ke pihak justru menambah mode gagal bila satu pihak kehilangan kunci.
- Temuan samping dari uji lokal: exec_prompt di Direct Mode mengembalikan dict bila respons mock berupa JSON. get_judgement di judge dan appeal sekarang menerima dict maupun str. Ini perbaikan ketahanan, bukan perubah perilaku di runtime nyata (di sana exec_prompt mengembalikan str).

## Uji lokal (genlayer-test Direct Mode, 20 Nov 2026)
- 15/15 LULUS dalam 0,90 detik. Cakupan: create/fund/cancel/claim/judge/appeal/waive/finalize, pembalikan verdict lewat appeal, split, semua jalur revert (nilai nol, seller sama dengan buyer, jumlah fund salah, fund oleh bukan seller, klaim ganda, klaim oleh bukan pihak, judge sebelum klaim lengkap, finalize sebelum banding selesai, finalize ganda, klaim terlalu panjang, stake di atas cap).
- Batasan uji: kontrak diuji sebagai salinan yang byte-identik kecuali header (pin SDK 1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6, satu-satunya runner di bundle GenVM v0.3.0-rc7) dan dua penyesuaian API era lama (from genlayer import * sebagai ganti from genlayer.types import *, gl.Contract sebagai ganti gl.contract.Contract). Kontrak kirim tetap memakai header v0.4.0 dan pin kzybg95x1gn21dw72m7hyg0maaap04n4nx55j9yt6fkdqxtz6bz0. Bukti deploy Studio tetap menjadi cek otoritatif untuk pin kirim.
- genvm-lint check LULUS (3 checks). Validasi schema linter gagal karena linter hanya punya cache GenVM v0.3.0-rc7 dan tidak ada tarball SDK untuk pin mana pun. Bukan salah kontrak, template resmi wizard_of_coin.py gagal dengan pola yang sama.

## File aktif
- contracts/fairdeal.py (kontrak utama, 12.6 KB)
- tests/test_fairdeal.py (15 uji lokal)
- README.md (audit teks nol pelanggaran: tanpa em/en dash, tanpa kosakata klise AI)

## Alamat / hash
- Studio deploy: belum ada (menunggu browser task)
- Repo GitHub: https://github.com/Yogii123-qw/genlayer-fairdeal-escrow
- Commit: 57b8e5a661d215d5c07149a0b147d7801df13f2a (main, terverifikasi di remote)

## Langkah berikutnya
1. Serahkan ke induk untuk uji deploy Studio lewat cloud browser (akun dev Studio, bukan wallet Monch). Tempel kontrak, deploy, panggil create_deal/fund/submit_claim/judge/finalize sampai ada transaksi ACCEPTED dan consensus tercapai. Catat alamat kontrak dan tx hash.
2. Setelah deploy Studio terverifikasi, serahkan draf submission ke Monch untuk disetujui. JANGAN submit ke Portal tanpa itu.
