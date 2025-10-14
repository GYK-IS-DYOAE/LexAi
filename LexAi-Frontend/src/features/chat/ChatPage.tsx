import { useEffect, useState, useRef } from "react";
import { useLocation } from "react-router-dom";
import { Paperclip, Send, Loader2 } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface Message {
  role: "user" | "assistant";
  content: string;
}

interface ChatItem {
  id: number;
  title: string;
  messages: Message[];
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [welcomeShown, setWelcomeShown] = useState(true);
  const [file, setFile] = useState<File | null>(null);
  const [isResponding, setIsResponding] = useState(false); // 🤖 model cevap veriyor mu

  const location = useLocation();
  const [chatId, setChatId] = useState<string | null>(null);
  const tempChatId = useRef<number | null>(null);

  // ✅ URL değiştiğinde chatId’yi güncelle
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const id = params.get("id");
    setChatId(id);
  }, [location.search]);

  // ✅ Mevcut sohbeti yükle
  useEffect(() => {
    const savedChats: ChatItem[] = JSON.parse(
      localStorage.getItem("chat_history_full") || "[]"
    );

    if (chatId) {
      const existingChat = savedChats.find(
        (chat) => chat.id === Number(chatId)
      );
      if (existingChat) {
        setMessages(existingChat.messages);
        setWelcomeShown(false);
      } else {
        setMessages([]);
        setWelcomeShown(true);
      }
    } else {
      setMessages([]);
      setWelcomeShown(true);
    }
  }, [chatId]);

  // ✅ Mesaj gönderme
  const sendMessage = () => {
    if (isResponding || (!input.trim() && !file)) return;

    const fileText = file ? `📎 Dosya: ${file.name}` : "";
    const newUserMessage: Message = {
      role: "user",
      content: [input.trim(), fileText].filter(Boolean).join("\n"),
    };

    const updatedMessages = [...messages, newUserMessage];
    setMessages(updatedMessages);
    setInput("");
    setFile(null);
    setWelcomeShown(false);
    setIsResponding(true); // 🤖 model cevap başlıyor

    const idToUse = saveChatToLocal(updatedMessages);

    if (!chatId) {
      window.history.replaceState(null, "", `/chat?id=${idToUse}`);
      setChatId(idToUse.toString());
      tempChatId.current = idToUse;
    }

    // 🧠 Demo amaçlı model cevabı (backend bağlanınca async API çağrısı buraya gelecek)
    setTimeout(() => {
      const assistantMessage: Message = {
        role: "assistant",
        content:
          "Bu modelin ilk cevabı olacak. (Gerçek model cevabı burada görünecek)",
      };
      const updatedWithAssistant = [...updatedMessages, assistantMessage];
      setMessages(updatedWithAssistant);
      saveChatToLocal(updatedWithAssistant);
      sessionStorage.setItem(
        "lexai_current_messages",
        JSON.stringify(updatedWithAssistant)
      );
      setIsResponding(false); // ✅ cevap tamamlandı
    }, 1500);
  };

  // ✅ Sohbet kaydetme
  const saveChatToLocal = (msgs: Message[]): number => {
    const fullChats: ChatItem[] = JSON.parse(
      localStorage.getItem("chat_history_full") || "[]"
    );

    const activeId =
      chatId ? Number(chatId) : tempChatId.current ? tempChatId.current : null;

    if (activeId) {
      const index = fullChats.findIndex((c) => c.id === activeId);
      if (index !== -1) {
        fullChats[index].messages = msgs;
      } else {
        const title =
          (msgs[0]?.content || "Yeni sohbet")
            .trim()
            .split(/\s+/)
            .slice(0, 3)
            .join(" ") + "...";
        fullChats.push({ id: activeId, title, messages: msgs });
      }

      localStorage.setItem("chat_history_full", JSON.stringify(fullChats));
      updateShortList(fullChats);
      return activeId;
    }

    const newId = Date.now();
    const title =
      (msgs[0]?.content || "Yeni sohbet")
        .trim()
        .split(/\s+/)
        .slice(0, 3)
        .join(" ") + "...";
    const newChat: ChatItem = { id: newId, title, messages: msgs };
    const updatedAll = [...fullChats, newChat];
    localStorage.setItem("chat_history_full", JSON.stringify(updatedAll));

    updateShortList(updatedAll);
    tempChatId.current = newId;
    return newId;
  };

  const updateShortList = (allChats: ChatItem[]) => {
    const shortList = allChats.map((c) => ({
      id: c.id,
      title: c.title,
    }));
    const unique = shortList.filter(
      (item, index, self) => index === self.findIndex((t) => t.id === item.id)
    );
    localStorage.setItem("chat_history", JSON.stringify(unique));
  };

  return (
    <div className="flex flex-col h-full bg-[hsl(var(--background))]">
      {/* Mesajlar Alanı */}
      <AnimatePresence mode="wait">
        <motion.main
          key={chatId}
          className="flex-1 overflow-y-auto p-6 space-y-4"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -10 }}
          transition={{ duration: 0.3 }}
        >
          {welcomeShown ? (
            <div className="flex items-center justify-center h-full">
              <p className="text-lg text-center text-[hsl(var(--foreground))]">
                Merhaba! Size nasıl yardımcı olabilirim?
              </p>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <motion.div
                key={idx}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
                className={`flex ${
                  msg.role === "assistant" ? "justify-start" : "justify-end"
                }`}
              >
                <div
                  className={`px-4 py-2 text-sm rounded-2xl max-w-[80%] break-words whitespace-pre-line ${
                    msg.role === "assistant"
                      ? "bg-[hsl(var(--muted))] text-[hsl(var(--foreground))]"
                      : "bg-[hsl(var(--lex-primary))] text-white"
                  }`}
                >
                  {msg.content}
                </div>
              </motion.div>
            ))
          )}
        </motion.main>
      </AnimatePresence>

      {/* Mesaj Yazma Alanı */}
      <div
        className="bg-[hsl(var(--background))] p-4 shadow-[0_-2px_6px_rgba(0,0,0,0.05)]"
      >
        <div className="flex items-center gap-2">
          {/* 📎 Dosya Ekleme */}
          <label
            htmlFor="file-upload"
            className="p-2 rounded-lg border border-[hsl(var(--border))]
                       hover:bg-[hsl(var(--muted))] cursor-pointer transition"
            title="Dosya Ekle"
          >
            <Paperclip size={18} className="text-[hsl(var(--foreground))]" />
          </label>
          <input
            id="file-upload"
            type="file"
            className="hidden"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />

          {/* Seçilen dosya */}
          {file && (
            <span className="text-xs text-[hsl(var(--muted-foreground))] truncate max-w-[150px]">
              {file.name}
            </span>
          )}

          {/* Mesaj input */}
          <input
            type="text"
            placeholder={
              isResponding
                ? "Model yanıt veriyor..."
                : "Mesajınızı yazın..."
            }
            value={input}
            disabled={isResponding}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            className={`flex-1 rounded-full border border-[hsl(var(--border))]
                       bg-[hsl(var(--card))] text-[hsl(var(--foreground))]
                       px-4 py-2 text-sm focus:outline-none focus:ring-2 
                       ${
                         isResponding
                           ? "opacity-60 cursor-not-allowed"
                           : "focus:ring-[hsl(var(--lex-primary))]"
                       }`}
          />

          {/* Gönder Butonu */}
          <button
            onClick={sendMessage}
            disabled={isResponding}
            className={`p-2 rounded-full transition flex items-center justify-center
                        ${
                          isResponding
                            ? "bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))] cursor-not-allowed"
                            : "bg-[hsl(var(--lex-primary))] text-white hover:opacity-90"
                        }`}
            title={isResponding ? "Model yanıt veriyor..." : "Gönder"}
          >
            {isResponding ? (
              <Loader2 size={18} className="animate-spin" />
            ) : (
              <Send size={18} />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}
