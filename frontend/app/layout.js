import { Noto_Sans_Thai, Inter } from "next/font/google";
import "./globals.css";

const notoSansThai = Noto_Sans_Thai({
  subsets: ["thai", "latin"],
  weight: ["300", "400", "500", "600", "700"],
  variable: "--font-noto-thai",
  display: "swap",
});

const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-inter",
  display: "swap",
});

const BASE_URL = process.env.NEXT_PUBLIC_SITE_URL || "https://www.agentic-auditor.com";

export const metadata = {
  title: "Business Health Assessment | Agentic-Auditor",
  description:
    "ประเมินสุขภาพธุรกิจ 7 มิติ ใช้เวลา 10–12 นาที รองรับ 8 ประเภทธุรกิจ AI วิเคราะห์เฉพาะธุรกิจของคุณ — โดย Agentic-Auditor",
  metadataBase: new URL(BASE_URL),
  openGraph: {
    type: "website",
    url: BASE_URL,
    title: "รู้จุดอ่อนธุรกิจก่อนที่ปัญหาจะลุกลาม | Agentic-Auditor BHA",
    description:
      "ประเมินสุขภาพธุรกิจ 7 มิติ ใช้เวลา 10–12 นาที รองรับ 8 ประเภทธุรกิจ AI วิเคราะห์เฉพาะธุรกิจของคุณ",
    siteName: "Agentic-Auditor",
    images: [{ url: "/og-image.png", width: 1200, height: 630, alt: "Agentic-Auditor BHA" }],
    locale: "th_TH",
  },
  twitter: {
    card: "summary_large_image",
    title: "รู้จุดอ่อนธุรกิจก่อนที่ปัญหาจะลุกลาม | Agentic-Auditor BHA",
    description: "ประเมินสุขภาพธุรกิจ 7 มิติ ใช้เวลา 10–12 นาที — ฟรี",
    images: ["/og-image.png"],
  },
  robots: { index: true, follow: true },
  themeColor: "#0F1E44",
};

export default function RootLayout({ children }) {
  return (
    <html lang="th">
      <body className={`${notoSansThai.variable} ${inter.variable} font-sans antialiased`}>
        {children}
      </body>
    </html>
  );
}
