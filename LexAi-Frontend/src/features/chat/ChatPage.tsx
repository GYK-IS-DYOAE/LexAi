import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Loader2, Paperclip, Send } from "lucide-react";
import api from "@/lib/api";
import FeedbackButtons, { type Vote } from "@/features/chat/FeedbackButtons";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface Message {
  id: string;
  sender: "user" | "assistant";
  content: string;
  vote?: Vote | null;
  feedback_id?: string | null;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [isResponding, setIsResponding] = useState(false);
  const [displayedText, setDisplayedText] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);

  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const navigate = useNavigate();
  const location = useLocation();

  // URL'deki id varsa yükle
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const id = params.get("id");
    if (id && /^[0-9a-fA-F-]{36}$/.test(id)) {
      setSessionId(id);
      loadMessages(id);
    } else {
      setMessages([]);
      setSessionId(null);
    }
  }, [location.search]);

  useEffect(() => {
    const resetHandler = () => {
      setSessionId(null);
      setMessages([]);
    };

    window.addEventListener("reset-chat", resetHandler);
    return () => window.removeEventListener("reset-chat", resetHandler);
  }, []);

  // Mesaj geçmişini yükle
  const loadMessages = async (id: string) => {
    try {
      const res = await api.get(`/conversation/session/${id}`);
      const msgs = res.data.messages.map((m: any) => ({
        id: m.id,
        sender: m.sender,
        content: m.content,
        vote: m.vote ?? null,
        feedback_id: m.feedback_id ?? null,
      }));
      setMessages(msgs);
    } catch (err) {
      console.error("Sohbet geçmişi yüklenemedi:", err);
    }
  };

  // Feedback butonları
  const handleFeedback = async (messageId: string, vote: Vote) => {
    const msg = messages.find((m) => m.id === messageId);
    const fid = msg?.feedback_id;
    if (!fid) return console.warn("Feedback ID bulunamadı");

    setMessages((prev) =>
      prev.map((m) => (m.id === messageId ? { ...m, vote } : m))
    );

    try {
      await api.patch(`/feedback/${fid}/vote`, { vote });
    } catch (err) {
      console.error("Feedback gönderilemedi:", err);
    }
  };

  // Mesaj gönderme
  const sendMessage = async () => {
    if (isResponding || !input.trim()) return;

    const formatted =
      input.trim().charAt(0).toUpperCase() + input.trim().slice(1);

    const userMsg: Message = {
      id: crypto.randomUUID(),
      sender: "user",
      content: formatted,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setIsResponding(true);
    setDisplayedText("");

    try {
      const res = await api.post("/ask", {
        query: formatted,
        session_id: sessionId,
      });

      const { answer, session_id, answer_id, feedback_id } = res.data;

      // Yeni session oluştuysa kaydet
      if (!sessionId && session_id) {
        setSessionId(session_id);
        navigate(`/chat?id=${session_id}`, { replace: true });

        try {
          await api.patch(`/conversation/session/${session_id}`, {
            title: formatted.slice(0, 50),
          });
        } catch (err) {
          console.warn("Sohbet başlığı kaydedilemedi:", err);
        }

        window.dispatchEvent(new Event("refresh-sessions"));
      }

      // Yazma efekti
      let i = 0;
      const interval = setInterval(() => {
        if (i <= answer.length) {
          i++;
        } else {
          clearInterval(interval);
          const botMsg: Message = {
            id: answer_id,
            sender: "assistant",
            content: answer,
            vote: null,
            feedback_id,
          };
          setMessages((prev) => [...prev, botMsg]);
          setDisplayedText("");
          setIsResponding(false);
          setTimeout(() => textareaRef.current?.focus(), 150);
        }
      }, 25);
    } catch (err) {
      console.error("Mesaj gönderilemedi:", err);
      setIsResponding(false);
    }
  };

  // Silme işlemi (sohbetin tamamını sil)
  const handleDeleteSession = async () => {
    if (!sessionId) return;
    try {
      await api.delete(`/conversation/session/${sessionId}`);
      setMessages([]);
      setSessionId(null);
      navigate("/chat", { replace: true });
      window.dispatchEvent(new Event("refresh-sessions"));
    } catch (err) {
      console.error("Sohbet silinemedi:", err);
    }
  };

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, displayedText]);

  useEffect(() => {
    if (!textareaRef.current) return;
    const el = textareaRef.current;
    el.style.height = "auto";
    el.style.height = Math.min(el.scrollHeight, 150) + "px";
  }, [input]);

  const hasMessages = messages.length > 0 || !!displayedText;

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)] bg-[hsl(var(--background))] overflow-x-hidden overflow-y-hidden">
      
      {/* --- Mesaj Alanı --- */}
      <div
        className={`flex-1 flex justify-center overflow-y-auto px-6 py-6 ${
          hasMessages ? "scrollbar-thin" : "overflow-hidden"
        }`}
      >
        <div className="w-full max-w-3xl">
          {!hasMessages ? (
            <div className="flex justify-center items-center h-full">
              <p className="text-lg text-[hsl(var(--foreground))]/80">
                Merhaba! Size nasıl yardımcı olabilirim?
              </p>
            </div>
          ) : (
            <>
              {messages.map((m, idx) => {
                const isUser = m.sender === "user";
                return (
                  <div
                    key={idx}
                    className={`flex mb-5 ${
                      isUser ? "justify-end" : "justify-start"
                    }`}
                  >
                    {isUser ? (
                      <div
                        className="px-4 py-2 text-sm rounded-2xl max-w-[80%] break-words whitespace-pre-line shadow-sm 
                        dark:bg-[hsl(var(--muted)/0.6)] bg-[hsl(var(--muted)/0.9)] text-[hsl(var(--foreground))]"
                      >
                        {m.content}
                      </div>
                    ) : (
                      <div className="max-w-[75ch] text-[hsl(var(--foreground))] leading-7">
                        <ReactMarkdown
                          remarkPlugins={[remarkGfm]}
                          components={{
                            p: ({ node, ...props }) => (
                              <p
                                className="leading-7 text-[hsl(var(--foreground))] whitespace-pre-line"
                                {...props}
                              />
                            ),
                            strong: ({ node, ...props }) => (
                              <strong
                                className="font-semibold text-[hsl(var(--foreground))]"
                                {...props}
                              />
                            ),
                            ul: ({ node, ...props }) => (
                              <ul className="list-disc ml-5 space-y-1" {...props} />
                            ),
                            ol: ({ node, ...props }) => (
                              <ol
                                className="list-decimal ml-5 space-y-1"
                                {...props}
                              />
                            ),
                            li: ({ node, ...props }) => <li {...props} />,
                          }}
                        >
                          {m.content}
                        </ReactMarkdown>

                        <div className="mt-2">
                          <FeedbackButtons
                            vote={m.vote ?? null}
                            onVote={(v) => handleFeedback(m.id, v)}
                          />
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}

              {displayedText && (
                <div className="flex justify-start">
                  <p className="text-[hsl(var(--foreground))] leading-7 whitespace-pre-line">
                    {displayedText}
                    <span className="ml-1 animate-pulse">|</span>
                  </p>
                </div>
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>
      </div>

      {/* --- Input Alanı --- */}
      <div className="sticky bottom-0 dark:bg-[hsl(var(--background))]/95 bg-[hsl(var(--muted)/0.7)] backdrop-blur-xl px-6 py-5 border-t border-[hsl(var(--muted)/0.3)] transition-colors duration-200">
        <div className="flex items-center gap-3 max-w-3xl mx-auto w-full rounded-2xl bg-[hsl(var(--muted)/0.4)] px-5 py-2.5 focus-within:ring-2 focus-within:ring-[hsl(var(--lex-primary))/0.4)] shadow-[0_4px_15px_rgba(0,0,0,0.08)] transition-all">
          <label
            htmlFor="file-upload"
            className="p-2 rounded-full hover:bg-[hsl(var(--muted))/0.5)] cursor-pointer transition flex-shrink-0"
          >
            <Paperclip size={18} className="text-[hsl(var(--foreground))]/80" />
          </label>
          <input
            id="file-upload"
            type="file"
            className="hidden"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />

          <textarea
            ref={textareaRef}
            rows={1}
            placeholder={
              isResponding ? "Model yanıt veriyor..." : "Mesajınızı yazın..."
            }
            value={input}
            disabled={isResponding}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) =>
              e.key === "Enter" && !e.shiftKey && sendMessage()
            }
            className={`flex-1 resize-none bg-transparent text-[hsl(var(--foreground))] text-sm placeholder:text-[hsl(var(--muted-foreground))]/70 focus:outline-none ${
              isResponding ? "opacity-60 cursor-not-allowed" : ""
            }`}
            style={{
              maxHeight: "150px",
              overflowY:
                textareaRef.current &&
                textareaRef.current.scrollHeight > 150
                  ? "auto"
                  : "hidden",
            }}
          />

          <button
            onClick={sendMessage}
            disabled={isResponding}
            className={`p-2.5 rounded-full transition-all duration-200 flex items-center justify-center shrink-0 ${
              isResponding
                ? "bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))]"
                : "bg-[hsl(var(--lex-primary))] text-white hover:scale-110 hover:shadow-[0_0_15px_hsl(var(--lex-primary)/0.5)]"
            }`}
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
