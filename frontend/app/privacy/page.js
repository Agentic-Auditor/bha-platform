import Link from "next/link";

export const metadata = { title: "นโยบายความเป็นส่วนตัว — Northstar BHA" };

export default function PrivacyPage() {
  return (
    <main className="min-h-screen bg-surface px-4 py-12">
      <div className="max-w-2xl mx-auto space-y-8">
        <div>
          <Link href="/" className="text-xs text-ink-muted hover:text-ink">← กลับหน้าแรก</Link>
          <h1 className="text-2xl font-bold text-navy mt-4 mb-1">นโยบายความเป็นส่วนตัว</h1>
          <p className="text-xs text-ink-faint">สอดคล้องกับ พ.ร.บ. คุ้มครองข้อมูลส่วนบุคคล พ.ศ. 2562 (PDPA)</p>
        </div>

        {[
          {
            title: "1. ข้อมูลที่เราเก็บ",
            body: "เราเก็บชื่อ อีเมล ประเภทธุรกิจ และคำตอบแบบประเมิน (ไม่มีข้อมูลส่วนบุคคลที่ละเอียดอ่อน) รวมถึงหลักฐานการชำระเงิน (สลิป) ที่คุณอัปโหลด",
          },
          {
            title: "2. วัตถุประสงค์การใช้ข้อมูล",
            body: "ข้อมูลใช้เพื่อ (1) วิเคราะห์และสร้างรายงานสุขภาพธุรกิจ (2) ส่งรายงาน PDF ทางอีเมล (3) ปรับปรุงความแม่นยำของระบบ AI ในรูปแบบ aggregate และไม่ระบุตัวตน",
          },
          {
            title: "3. การเปิดเผยข้อมูล",
            body: "เราไม่ขาย ไม่ให้เช่า และไม่แบ่งปันข้อมูลส่วนบุคคลแก่บุคคลภายนอก ยกเว้นที่กฎหมายกำหนด ผู้ให้บริการ Cloud (Railway, Vercel) มีการเข้าถึงข้อมูลในฐานะผู้ประมวลผลข้อมูล",
          },
          {
            title: "4. ระยะเวลาเก็บข้อมูล",
            body: "ข้อมูลแบบประเมินและรายงานจะเก็บไว้ 2 ปีหลังจากวันที่ทำแบบประเมิน สลิปการชำระเงินเก็บไว้ 5 ปีตามกฎหมายภาษี",
          },
          {
            title: "5. สิทธิ์ของท่าน (PDPA)",
            body: "ท่านมีสิทธิ์ขอเข้าถึง แก้ไข ลบ หรือคัดค้านการประมวลผลข้อมูลของท่านได้ ติดต่อเราทางอีเมลด้านล่าง เราจะตอบกลับภายใน 30 วัน",
          },
          {
            title: "6. ความปลอดภัย",
            body: "ข้อมูลทั้งหมดเข้ารหัสระหว่างส่ง (HTTPS/TLS) และจัดเก็บในฐานข้อมูลที่มีการยืนยันตัวตน เราไม่เก็บรหัสผ่านในรูปแบบ plaintext",
          },
        ].map((s) => (
          <section key={s.title} className="bg-card rounded-card shadow-card px-5 py-4">
            <h2 className="text-sm font-semibold text-navy mb-2">{s.title}</h2>
            <p className="text-sm text-ink-muted leading-relaxed">{s.body}</p>
          </section>
        ))}

        <p className="text-xs text-ink-faint text-center">
          ผู้ควบคุมข้อมูล: Northstar Corporation ·{" "}
          <a href="mailto:hello@northstar.co.th" className="underline hover:text-ink">
            hello@northstar.co.th
          </a>
        </p>
      </div>
    </main>
  );
}
