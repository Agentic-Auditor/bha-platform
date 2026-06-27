import Link from "next/link";

export const metadata = { title: "เงื่อนไขการใช้บริการ — Northstar BHA" };

export default function TermsPage() {
  return (
    <main className="min-h-screen bg-surface px-4 py-12">
      <div className="max-w-2xl mx-auto space-y-8">
        <div>
          <Link href="/" className="text-xs text-ink-muted hover:text-ink">← กลับหน้าแรก</Link>
          <h1 className="text-2xl font-bold text-navy mt-4 mb-1">เงื่อนไขการใช้บริการ</h1>
          <p className="text-xs text-ink-faint">มีผลตั้งแต่วันที่ 1 มกราคม 2568</p>
        </div>

        {[
          {
            title: "1. การยอมรับเงื่อนไข",
            body: "การใช้บริการ Business Health Assessment (BHA) ของ Northstar Corporation ถือว่าคุณยอมรับเงื่อนไขการใช้บริการฉบับนี้ทั้งหมด หากไม่ยอมรับ กรุณาหยุดใช้บริการ",
          },
          {
            title: "2. ขอบเขตบริการ",
            body: "BHA ให้บริการเครื่องมือประเมินสุขภาพธุรกิจ ผลลัพธ์ที่ได้เป็นข้อมูลประกอบการตัดสินใจ ไม่ใช่คำแนะนำทางกฎหมาย การเงิน หรือการลงทุน Northstar Corporation ไม่รับผิดชอบต่อความเสียหายที่เกิดจากการนำผลลัพธ์ไปใช้",
          },
          {
            title: "3. การชำระเงิน",
            body: "ค่าบริการรายงานฉบับเต็ม ฿499 ต่อครั้ง ชำระผ่าน PromptPay และอัปโหลดสลิป ทีมงานจะตรวจสอบภายใน 30 นาที หากสลิปไม่ผ่าน คุณสามารถอัปโหลดใหม่ได้ ไม่มีการคืนเงินหลังจากที่รายงานถูกส่งแล้ว",
          },
          {
            title: "4. ทรัพย์สินทางปัญญา",
            body: "เนื้อหา คำถาม อัลกอริทึม และรายงานทั้งหมดเป็นทรัพย์สินของ Northstar Corporation คุณได้รับสิทธิ์ใช้รายงานส่วนตัวเท่านั้น ห้ามนำไปเผยแพร่เชิงพาณิชย์",
          },
          {
            title: "5. การแก้ไขเงื่อนไข",
            body: "Northstar Corporation ขอสงวนสิทธิ์แก้ไขเงื่อนไขนี้ได้ตลอดเวลา การใช้บริการต่อหลังการแก้ไขถือว่ายอมรับเงื่อนไขใหม่",
          },
        ].map((s) => (
          <section key={s.title} className="bg-card rounded-card shadow-card px-5 py-4">
            <h2 className="text-sm font-semibold text-navy mb-2">{s.title}</h2>
            <p className="text-sm text-ink-muted leading-relaxed">{s.body}</p>
          </section>
        ))}

        <p className="text-xs text-ink-faint text-center">
          ติดต่อ:{" "}
          <a href="mailto:hello@northstar.co.th" className="underline hover:text-ink">
            hello@northstar.co.th
          </a>
        </p>
      </div>
    </main>
  );
}
