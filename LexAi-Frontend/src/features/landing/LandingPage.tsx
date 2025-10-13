import { motion } from "framer-motion";
import { Link } from "react-router-dom";

export default function LandingPage() {
  return (
    <div className="min-h-screen bg-[#f8f9fa] dark:bg-[#0f0f10] text-[#1a1a1a] dark:text-gray-100 transition-colors duration-300">

      {/* HERO SECTION */}
      <section className="flex flex-col items-center text-center max-w-3xl mx-auto py-28 px-4">
        <motion.h1
          className="text-5xl font-extrabold mb-6 bg-gradient-to-r from-[hsl(var(--lex-primary-grad1))] to-[hsl(var(--lex-primary-grad2))] bg-clip-text text-transparent"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8 }}
        >
          LexAI’ye Hoş Geldiniz
        </motion.h1>

        <motion.p
          className="text-lg text-gray-700 dark:text-gray-300 mb-10 leading-relaxed"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2, duration: 0.8 }}
        >
          Yapay zekâ destekli dava yönlendirme ve emsal öneri asistanı.
          <br />
          Hukuk teknolojisinde güven, doğruluk ve hız için tasarlandı.
        </motion.p>

        <motion.div
          className="flex flex-wrap justify-center gap-4"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.4, duration: 0.8 }}
        >
          <Link
            to="/login"
            className="px-8 py-3 rounded-2xl bg-gradient-to-r from-[hsl(var(--lex-primary-grad1))] to-[hsl(var(--lex-primary-grad2))] text-white font-semibold shadow-md hover:brightness-110 transition"
          >
            Giriş Yap
          </Link>
          <Link
            to="/register"
            className="px-8 py-3 rounded-2xl border border-[hsl(var(--lex-primary))] text-[hsl(var(--lex-primary))] font-semibold hover:bg-[hsl(var(--lex-primary))/0.08] transition"
          >
            Kayıt Ol
          </Link>
        </motion.div>
      </section>

      {/* ROADMAP SECTION */}
      <section className="py-24 px-6 bg-white dark:bg-[#1a1a1d] text-center shadow-inner">
        <motion.h2
            className="text-3xl font-bold mb-12 text-[hsl(var(--lex-primary))]"
            initial={{ opacity: 0, y: 40 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: false, amount: 0.3 }}
            transition={{ duration: 1.2, ease: [0.25, 0.1, 0.25, 1] }} // soft-in-out
        >
            LexAI Nasıl Çalışır?
        </motion.h2>

        <motion.div
            className="grid md:grid-cols-3 gap-8 max-w-6xl mx-auto"
            initial="hidden"
            whileInView="visible"
            viewport={{ once: false, amount: 0.3 }}
            variants={{
            hidden: {},
            visible: {
                transition: {
                staggerChildren: 0.08, // çok küçük aralık
                },
            },
            }}
        >
            {[
            {
                step: "1",
                title: "Veriyi Anlar",
                desc: "Yargıtay kararlarını, mevzuatları ve kullanıcı sorgularını analiz eder.",
            },
            {
                step: "2",
                title: "Hukuki Bağlamı Kurar",
                desc: "Yapay zekâ, benzer davaları ve kanun maddelerini eşleştirir.",
            },
            {
                step: "3",
                title: "Sonuç Önerir",
                desc: "Kullanıcıya en uygun emsal kararı ve hukuki argümanı sunar.",
            },
            ].map((item, i) => (
            <motion.div
                key={i}
                variants={{
                hidden: { opacity: 0, y: 60, scale: 0.97 },
                visible: {
                    opacity: 1,
                    y: 0,
                    scale: 1,
                    transition: {
                    duration: 1.6, // yavaşça açılıyor
                    ease: [0.22, 1, 0.36, 1], // cubic-bezier, premium slow-out
                    type: "tween",
                    },
                },
                }}
                className="bg-gray-50 dark:bg-[#131315] rounded-2xl p-8 shadow-lg hover:shadow-xl transition border border-gray-200 dark:border-gray-700"
            >
                <div className="w-14 h-14 mx-auto flex items-center justify-center rounded-full bg-gradient-to-r from-[hsl(var(--lex-primary-grad1))] to-[hsl(var(--lex-primary-grad2))] text-white text-xl font-bold mb-4 shadow-md">
                {item.step}
                </div>
                <h3 className="text-xl font-semibold mb-2">{item.title}</h3>
                <p className="text-gray-600 dark:text-gray-400 text-sm leading-relaxed">
                {item.desc}
                </p>
            </motion.div>
            ))}
        </motion.div>
        </section>
    </div>
  );
}
