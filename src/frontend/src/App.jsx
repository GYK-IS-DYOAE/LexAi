import React, { createContext, useContext, useState, useEffect, useRef } from "react";
import { BrowserRouter, Routes, Route, Link, useNavigate, Navigate } from "react-router-dom";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { 
  Copy, Moon, Sun, LogOut, Send, Scale, FileText, 
  MessageSquare, Shield, CheckCircle, AlertTriangle, 
  Users, Book, Sparkles, TrendingUp, Clock, Search
} from "lucide-react";
import axios from 'axios';

// LexAI - Gerçek API entegrasyonlu hukuk asistanı

const AuthContext = createContext(null);
function useAuth() { return useContext(AuthContext); }

// API Configuration
const API_BASE_URL = 'http://localhost:8000';

export default function LexAIMultiPage() {
  const [darkMode, setDarkMode] = useState(true);
  const [currentUser, setCurrentUser] = useState(null);
  const [token, setToken] = useState(null);

  // Check auth on mount
  useEffect(() => {
    const savedToken = localStorage.getItem('token');
    const savedUser = localStorage.getItem('user');
    if (savedToken && savedUser) {
      setToken(savedToken);
      setCurrentUser(JSON.parse(savedUser));
    }
  }, []);

  const register = async (data) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/auth/register`, {
        username: data.username,
        email: data.email,
        password: data.password
      });
      setToken(response.data.access_token);
      setCurrentUser(response.data.user);
      localStorage.setItem('token', response.data.access_token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
      return { ok: true };
    } catch (error) {
      return { ok: false, error: error.response?.data?.detail || error.message };
    }
  };

  const login = async (email, password) => {
    try {
      const response = await axios.post(`${API_BASE_URL}/api/auth/login`, {
        email,
        password
      });
      setToken(response.data.access_token);
      setCurrentUser(response.data.user);
      localStorage.setItem('token', response.data.access_token);
      localStorage.setItem('user', JSON.stringify(response.data.user));
      return { ok: true };
    } catch (error) {
      return { ok: false, error: error.response?.data?.detail || error.message };
    }
  };

  const logout = () => {
    setCurrentUser(null);
    setToken(null);
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  };

  return (
    <AuthContext.Provider value={{ currentUser, token, register, login, logout, darkMode, setDarkMode }}>
      <BrowserRouter>
        <div className={`min-h-screen transition-colors duration-300 ${
          darkMode 
            ? 'bg-gradient-to-br from-[#2A2A2A] via-[#3A3A3A] to-[#4A4A4A] text-gray-100' 
            : 'bg-gradient-to-br from-[#FAF9F6] via-[#F8F6F3] to-[#F0EDE8] text-gray-900'
        }`}>
          <div className="max-w-7xl mx-auto p-6">
            <header className="flex items-center justify-between mb-6">
              <Link to="/" className="flex items-center gap-3 group">
                <div className="relative w-14 h-14 rounded-xl bg-gradient-to-br from-[#7A3B48] via-[#96394A] to-[#B14556] flex items-center justify-center text-white font-bold text-xl shadow-lg hover:shadow-2xl hover:scale-110 transition-all duration-300">
                  <div className="absolute inset-0 bg-white opacity-10 rounded-xl"></div>
                  <span className="relative z-10">LA</span>
                </div>
                <div>
                  <h1 className={`text-2xl font-bold ${darkMode ? 'text-[#B14556]' : 'text-[#7A3B48]'}`}>LexAI</h1>
                  <div className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>Hukuk asistanı — Sorunlarınızı hukuk kapsamında analiz edin</div>
                </div>
              </Link>

              <nav className="flex items-center gap-3">
                {currentUser ? (
                  <>
                    <span className={`text-sm ${darkMode ? 'text-gray-300' : 'text-gray-600'}`}>Hoş geldiniz, <strong>{currentUser.username}</strong></span>
                    <Link to="/app"><Button className="bg-[#7A3B48] hover:bg-[#96394A] text-white">Uygulamaya Git</Button></Link>
                    {currentUser.is_admin && <Link to="/admin"><Button className={`${darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-300 hover:bg-gray-400'} text-white`}>Admin</Button></Link>}
                    <Button className={`${darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-300 hover:bg-gray-400'} text-white flex items-center gap-1`} onClick={logout}><LogOut size={16} /> Çıkış</Button>
                  </>
                ) : (
                  <>
                    <Link to="/login"><Button className="bg-[#7A3B48] hover:bg-[#96394A] text-white">Giriş Yap</Button></Link>
                    <Link to="/register"><Button className={`${darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-300 hover:bg-gray-400'} text-white`}>Kayıt Ol</Button></Link>
                  </>
                )}

                <Button className={`${darkMode ? 'bg-[#96394A] hover:bg-[#B14556]' : 'bg-gray-200 hover:bg-gray-300'} text-white flex items-center gap-1`} onClick={() => setDarkMode(d => !d)}>
                  {darkMode ? <Sun size={14} /> : <Moon size={14} />}
                </Button>
              </nav>
            </header>

            <main>
              <Routes>
                <Route path="/" element={<LandingPage />} />
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<RegisterPage />} />
                <Route path="/app" element={<ProtectedRoute><AppPage /></ProtectedRoute>} />
                <Route path="/admin" element={<ProtectedRoute adminOnly><AdminPage /></ProtectedRoute>} />
              </Routes>
            </main>

            <footer className="mt-12 text-center text-sm text-gray-400">© 2025 LexAI</footer>
          </div>
        </div>
      </BrowserRouter>
    </AuthContext.Provider>
  );
}

function LandingPage() {
  const { darkMode } = useAuth();
  return (
    <div className="space-y-12 animate-fadeIn">
      {/* Hero Section */}
      <section className="text-center py-12">
        <div className="inline-flex items-center gap-2 bg-[#7A3B48]/20 px-4 py-2 rounded-full mb-6 border border-[#7A3B48]/30">
          <Sparkles className="w-4 h-4 text-[#B14556]" />
          <span className="text-sm text-[#E8C5C9]">Yapay Zeka Destekli Hukuk Asistanı</span>
        </div>
        <h1 className="text-5xl font-bold text-[#E8C5C9] mb-4 leading-tight">
          Hukuki Desteğe Erişim Artık Çok Daha Kolay
        </h1>
            <p className={`text-xl max-w-2xl mx-auto mb-8 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>
              LexAI, karşılaştığınız hukuki sorunları ya da karmaşık hukuki metinleri analiz eder, anlaşılır özetler sunar ve size rehberlik eder.
        </p>
        <div className="flex gap-4 justify-center">
          <Link to="/register">
                <Button className="bg-[#7A3B48] hover:bg-[#96394A] text-white px-8 py-6 text-lg transition-all transform hover:scale-105 shadow-lg flex items-center gap-2">
                  <Sparkles className="w-5 h-5" />
              Ücretsiz Başlayın
            </Button>
          </Link>
          <Link to="/login">
                <Button className={`${darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-200 hover:bg-gray-300 text-gray-900'} text-white px-8 py-6 text-lg transition-all transform hover:scale-105 shadow-lg`}>
              Giriş Yapın
            </Button>
          </Link>
        </div>
      </section>

      {/* Features Grid */}
      <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Card className="bg-[#3C2C34] border-[#7A3B48]/30 hover:border-[#B14556] transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-[#7A3B48]/20">
          <CardContent className="p-6">
            <div className="w-12 h-12 bg-[#7A3B48] rounded-lg flex items-center justify-center mb-4">
              <Scale className="w-6 h-6 text-white" />
            </div>
            <h3 className="text-lg font-semibold text-[#E8C5C9] mb-2">Akıllı Analiz</h3>
            <p className="text-gray-300 text-sm">Hukuki danışmanlık ihtiyacını erken aşamada karşılar</p>
          </CardContent>
        </Card>

        <Card className="bg-[#3C2C34] border-[#7A3B48]/30 hover:border-[#B14556] transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-[#7A3B48]/20">
          <CardContent className="p-6">
            <div className="w-12 h-12 bg-[#96394A] rounded-lg flex items-center justify-center mb-4">
              <Book className="w-6 h-6 text-white" />
            </div>
            <h3 className="text-lg font-semibold text-[#E8C5C9] mb-2">Emsal Tespiti</h3>
            <p className="text-gray-300 text-sm">Benzer davaları ve emsal kararları hızlıca bulur ve sunar.</p>
          </CardContent>
        </Card>

        <Card className="bg-[#3C2C34] border-[#7A3B48]/30 hover:border-[#B14556] transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-[#7A3B48]/20">
          <CardContent className="p-6">
            <div className="w-12 h-12 bg-[#7A3B48] rounded-lg flex items-center justify-center mb-4">
              <MessageSquare className="w-6 h-6 text-white" />
            </div>
            <h3 className="text-lg font-semibold text-[#E8C5C9] mb-2">Etkileşimli Danışma</h3>
            <p className="text-gray-300 text-sm">Sorularınızı sorun, detaylandırın ve rehberlik alın.</p>
          </CardContent>
        </Card>

        <Card className="bg-[#3C2C34] border-[#7A3B48]/30 hover:border-[#B14556] transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-[#7A3B48]/20">
          <CardContent className="p-6">
            <div className="w-12 h-12 bg-[#96394A] rounded-lg flex items-center justify-center mb-4">
              <Shield className="w-6 h-6 text-white" />
            </div>
            <h3 className="text-lg font-semibold text-[#E8C5C9] mb-2">Güvenli & Gizli</h3>
            <p className="text-gray-300 text-sm">Verileriniz şifreli ve güvende. Gizlilik garantisi.</p>
          </CardContent>
        </Card>

        <Card className="bg-[#3C2C34] border-[#7A3B48]/30 hover:border-[#B14556] transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-[#7A3B48]/20">
          <CardContent className="p-6">
            <div className="w-12 h-12 bg-[#96394A] rounded-lg flex items-center justify-center mb-4">
              <Clock className="w-6 h-6 text-white" />
            </div>
            <h3 className="text-lg font-semibold text-[#E8C5C9] mb-2">Hızlı Sonuçlar</h3>
            <p className="text-gray-300 text-sm">Anında analiz ve hızlı yanıtlar ile zamandan tasarruf.</p>
          </CardContent>
        </Card>

        <Card className="bg-[#3C2C34] border-[#7A3B48]/30 hover:border-[#B14556] transition-all duration-300 transform hover:scale-105 hover:shadow-xl hover:shadow-[#7A3B48]/20">
          <CardContent className="p-6">
            <div className="w-12 h-12 bg-[#7A3B48] rounded-lg flex items-center justify-center mb-4 text-2xl text-white">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                <circle cx="12" cy="12" r="10" stroke="white" strokeWidth="2"/>
                <circle cx="8" cy="10" r="1.5" fill="white"/>
                <circle cx="16" cy="10" r="1.5" fill="white"/>
                <path d="M8 16c1.5 2 4.5 2 6 0" stroke="white" strokeWidth="2" strokeLinecap="round"/>
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-[#E8C5C9] mb-2">Kullanıcı Dostu Arayüz</h3>
            <p className="text-gray-300 text-sm">Sade ve anlaşılır tasarım ile kolayca kullanın.</p>
          </CardContent>
        </Card>
      </section>

      {/* How It Works */}
      <section className="bg-[#3C2C34] border border-[#7A3B48]/30 rounded-xl p-8">
        <h2 className="text-3xl font-bold text-[#E8C5C9] text-center mb-8">Nasıl Çalışır?</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          <div className="text-center">
            <div className="w-16 h-16 bg-[#7A3B48] rounded-full flex items-center justify-center mx-auto mb-4 text-2xl font-bold text-white">1</div>
            <h3 className="text-lg font-semibold text-[#E8C5C9] mb-2">Belge Yükleyin</h3>
            <p className="text-gray-300 text-sm">Sorunuzu sorun veya dosya yükleyin</p>
          </div>
          <div className="text-center">
            <div className="w-16 h-16 bg-[#96394A] rounded-full flex items-center justify-center mx-auto mb-4 text-2xl font-bold text-white">2</div>
            <h3 className="text-lg font-semibold text-[#E8C5C9] mb-2">Soru Sorun</h3>
            <p className="text-gray-300 text-sm">Merak ettiklerinizi yazın ve gönder butonuna basın</p>
          </div>
          <div className="text-center">
            <div className="w-16 h-16 bg-[#7A3B48] rounded-full flex items-center justify-center mx-auto mb-4 text-2xl font-bold text-white">3</div>
            <h3 className="text-lg font-semibold text-[#E8C5C9] mb-2">Sonuç Alın</h3>
            <p className="text-gray-300 text-sm">Detaylı analiz ve önerilerle rehberlik alın</p>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="bg-gradient-to-r from-[#7A3B48] to-[#96394A] rounded-xl p-12 text-center shadow-2xl">
        <h2 className="text-3xl font-bold text-white mb-4">Hemen Başlayın</h2>
        <p className="text-gray-200 mb-6 max-w-2xl mx-auto">
          Ücretsiz hesap oluşturun ve LexAI gücünü keşfedin. Hukuki yardım almak hiç bu kadar kolay olmamıştı.
        </p>
        <div className="flex justify-center">
        <Link to="/register">
            <Button className="bg-white text-[#7A3B48] hover:bg-gray-100 px-8 py-6 text-lg font-semibold transition-all transform hover:scale-105 shadow-lg">
            Ücretsiz Kaydolun
          </Button>
        </Link>
        </div>
      </section>
    </div>
  );
}

function LoginPage() {
  const { login, darkMode } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    setLoading(true);
    setError(null);
    const res = await login(email, password);
    setLoading(false);
    if (!res.ok) setError(res.error);
    else navigate('/app');
  };

  return (
    <div className="max-w-md mx-auto">
      <Card className={`p-6 ${darkMode ? 'bg-[#3C2C34] border-gray-600' : 'bg-white border-gray-300'} shadow-xl`}>
        <CardHeader>
          <h2 className={`text-xl font-bold ${darkMode ? 'text-[#B14556]' : 'text-[#7A3B48]'}`}>Giriş Yap</h2>
        </CardHeader>
        <CardContent>
          {error && <div className={`text-sm ${darkMode ? 'text-red-400 bg-red-900/20' : 'text-red-600 bg-red-100'} mb-2 p-2 rounded`}>{error}</div>}
          <Label className={`${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>E-posta</Label>
          <Input value={email} onChange={(e) => setEmail(e.target.value)} className={`${darkMode ? 'bg-[#2E2A2B] border-gray-600 text-gray-200' : 'bg-gray-50 border-gray-300 text-gray-900'} mt-1`} />
          <Label className={`mt-3 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>Şifre</Label>
          <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} onKeyPress={(e) => e.key === 'Enter' && submit()} className={`${darkMode ? 'bg-[#2E2A2B] border-gray-600 text-gray-200' : 'bg-gray-50 border-gray-300 text-gray-900'} mt-1`} />
          <div className="flex gap-2 mt-4">
            <Button className="bg-[#7A3B48] hover:bg-[#96394A] text-white shadow-md" onClick={submit} disabled={loading}>{loading ? 'Giriş yapılıyor...' : 'Giriş'}</Button>
            <Link to="/register"><Button className={`${darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-200 hover:bg-gray-300 text-gray-900'} text-white shadow-md`}>Kayıt Ol</Button></Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function RegisterPage() {
  const { register, darkMode } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    setLoading(true);
    setError(null);
    const res = await register({ username, email, password });
    setLoading(false);
    if (!res.ok) setError(res.error);
    else navigate('/app');
  };

  return (
    <div className="max-w-md mx-auto">
      <Card className={`p-6 ${darkMode ? 'bg-[#3C2C34] border-gray-600' : 'bg-white border-gray-300'} shadow-xl`}>
        <CardHeader>
          <h2 className={`text-xl font-bold ${darkMode ? 'text-[#B14556]' : 'text-[#7A3B48]'}`}>Kayıt Ol</h2>
        </CardHeader>
        <CardContent>
          {error && <div className={`text-sm ${darkMode ? 'text-red-400 bg-red-900/20' : 'text-red-600 bg-red-100'} mb-2 p-2 rounded`}>{error}</div>}
          <Label className={`${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>Kullanıcı Adı</Label>
          <Input value={username} onChange={(e) => setUsername(e.target.value)} className={`${darkMode ? 'bg-[#2E2A2B] border-gray-600 text-gray-200' : 'bg-gray-50 border-gray-300 text-gray-900'} mt-1`} />
          <Label className={`mt-3 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>E-posta</Label>
          <Input value={email} onChange={(e) => setEmail(e.target.value)} className={`${darkMode ? 'bg-[#2E2A2B] border-gray-600 text-gray-200' : 'bg-gray-50 border-gray-300 text-gray-900'} mt-1`} />
          <Label className={`mt-3 ${darkMode ? 'text-gray-300' : 'text-gray-700'}`}>Şifre</Label>
          <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} onKeyPress={(e) => e.key === 'Enter' && submit()} className={`${darkMode ? 'bg-[#2E2A2B] border-gray-600 text-gray-200' : 'bg-gray-50 border-gray-300 text-gray-900'} mt-1`} />
          <div className="flex gap-2 mt-4">
            <Button className="bg-[#7A3B48] hover:bg-[#96394A] text-white shadow-md" onClick={submit} disabled={loading}>{loading ? 'Kayıt yapılıyor...' : 'Kayıt Ol'}</Button>
            <Link to="/login"><Button className={`${darkMode ? 'bg-gray-700 hover:bg-gray-600' : 'bg-gray-200 hover:bg-gray-300 text-gray-900'} text-white shadow-md`}>Giriş Yap</Button></Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function ProtectedRoute({ children, adminOnly = false }) {
  const { currentUser } = useAuth();
  
  if (!currentUser) {
    return <Navigate to="/login" />;
  }
  
  if (adminOnly && !currentUser.is_admin) {
    return <Navigate to="/app" />;
  }
  
  return children;
}

function AppPage() {
  const { darkMode } = useAuth();
  const [passages, setPassages] = useState("");
  const [question, setQuestion] = useState("");
  const [conversation, setConversation] = useState([]);
  const [loading, setLoading] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const conversationEndRef = useRef(null);

  const scrollToBottom = () => {
    conversationEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversation]);

  const send = async (fromChat = false) => {
    if (loading) return;
    
    const currentPassages = fromChat ? passages : passages;
    const currentQuestion = fromChat ? chatInput : question;
    
    if (!currentPassages.trim() || !currentQuestion.trim()) return;

    setLoading(true);
    
    const userMessage = { role: "user", content: currentQuestion };
    setConversation(prev => [...prev, userMessage]);

    try {
      const response = await axios.post(`${API_BASE_URL}/api/search`, {
        query: currentQuestion,
        passages: currentPassages,
        top_k: 5
      });

      const aiMessage = { 
        role: "assistant", 
        content: response.data.response || "Üzgünüm, şu anda yanıt veremiyorum." 
      };
      
      setConversation(prev => [...prev, aiMessage]);
      
      if (fromChat) {
        setChatInput("");
      } else {
        setQuestion("");
      }
    } catch (error) {
      const errorMessage = { 
        role: "assistant", 
        content: "Üzgünüm, bir hata oluştu. Lütfen tekrar deneyin." 
      };
      setConversation(prev => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      <div className="lg:col-span-1 space-y-4">
        {/* Önerilen Davalar */}
        <Card className="p-4 bg-[#3C2C34] border-[#7A3B48]/30 hover:border-[#B14556] transition-all">
          <CardHeader>
            <h3 className="text-lg font-semibold text-[#E8C5C9] flex items-center gap-2">
              <Scale className="w-5 h-5" />
              Önerilen Davalar
            </h3>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Dava Kartları */}
            <div className="space-y-3">
              <div className="bg-[#2E2A2B] border border-gray-600 rounded-lg p-4 hover:border-[#B14556] transition-all">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-[#7A3B48] rounded-full flex items-center justify-center flex-shrink-0">
                    <Scale className="w-4 h-4 text-white" />
                  </div>
                  <div className="flex-1">
                    <h4 className="text-sm font-semibold text-[#E8C5C9] mb-1">
                      İş Sözleşmesi Feshi Davası
                    </h4>
                    <p className="text-xs text-gray-400 mb-3 leading-relaxed">
                      İşveren tarafından haksız fesih edilen işçinin tazminat talebi. 
                      İş Kanunu maddeleri çerçevesinde değerlendirme.
                    </p>
                    <Button 
                      className="bg-[#7A3B48] hover:bg-[#96394A] text-xs py-1 px-3 transition-all"
                      onClick={() => setChatInput("İş sözleşmesi feshi hakkında bilgi verir misiniz?")}
                    >
                      Detayları Gör
                    </Button>
                  </div>
                </div>
              </div>

              <div className="bg-[#2E2A2B] border border-gray-600 rounded-lg p-4 hover:border-[#B14556] transition-all">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-[#96394A] rounded-full flex items-center justify-center flex-shrink-0">
                    <FileText className="w-4 h-4 text-white" />
                  </div>
                  <div className="flex-1">
                    <h4 className="text-sm font-semibold text-[#E8C5C9] mb-1">
                      Ticari Sözleşme İhlali
                    </h4>
                    <p className="text-xs text-gray-400 mb-3 leading-relaxed">
                      Sözleşme şartlarının ihlali durumunda tazminat hesaplama 
                      ve Borçlar Kanunu uygulamaları.
                    </p>
                    <Button 
                      className="bg-[#7A3B48] hover:bg-[#96394A] text-xs py-1 px-3 transition-all"
                      onClick={() => setChatInput("Ticari sözleşme ihlali durumunda ne yapabilirim?")}
                    >
                      Detayları Gör
                    </Button>
                  </div>
                </div>
              </div>

              <div className="bg-[#2E2A2B] border border-gray-600 rounded-lg p-4 hover:border-[#B14556] transition-all">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-[#7A3B48] rounded-full flex items-center justify-center flex-shrink-0">
                    <Shield className="w-4 h-4 text-white" />
                  </div>
                  <div className="flex-1">
                    <h4 className="text-sm font-semibold text-[#E8C5C9] mb-1">
                      Kişisel Veri Koruma
                    </h4>
                    <p className="text-xs text-gray-400 mb-3 leading-relaxed">
                      KVKK kapsamında kişisel veri ihlali durumlarında 
                      başvuru süreçleri ve tazminat hakları.
                    </p>
                    <Button 
                      className="bg-[#7A3B48] hover:bg-[#96394A] text-xs py-1 px-3 transition-all"
                      onClick={() => setChatInput("Kişisel veri ihlali durumunda nasıl başvuru yapabilirim?")}
                    >
                      Detayları Gör
                    </Button>
                  </div>
                </div>
              </div>

              <div className="bg-[#2E2A2B] border border-gray-600 rounded-lg p-4 hover:border-[#B14556] transition-all">
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 bg-[#96394A] rounded-full flex items-center justify-center flex-shrink-0">
                    <Users className="w-4 h-4 text-white" />
                  </div>
                  <div className="flex-1">
                    <h4 className="text-sm font-semibold text-[#E8C5C9] mb-1">
                      Aile Hukuku Davaları
                    </h4>
                    <p className="text-xs text-gray-400 mb-3 leading-relaxed">
                      Boşanma, nafaka ve velayet konularında 
                      Türk Medeni Kanunu uygulamaları.
                    </p>
                    <Button 
                      className="bg-[#7A3B48] hover:bg-[#96394A] text-xs py-1 px-3 transition-all"
                      onClick={() => setChatInput("Aile hukuku konularında bilgi alabilir miyim?")}
                    >
                      Detayları Gör
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="lg:col-span-2">
        {/* Ana Konuşma Alanı */}
        <Card className="bg-[#3C2C34] border-[#7A3B48]/30">
          <CardHeader>
            <h2 className="text-xl font-semibold text-[#E8C5C9] flex items-center gap-2">
              <MessageSquare className="w-5 h-5" />
              LexAI Hukuk Asistanı
            </h2>
          </CardHeader>
          <CardContent>
            {/* Konuşma Geçmişi */}
            <div className="bg-[#2E2A2B] rounded-lg p-4 mb-4 min-h-[400px] max-h-[500px] overflow-y-auto">
              {conversation.length === 0 ? (
                <div className="text-center text-gray-400 py-8">
                  <MessageSquare className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p className="text-sm">Henüz konuşma başlamadı. Aşağıdaki önerilen davalardan birini seçerek başlayabilirsiniz.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {conversation.map((msg, index) => (
                    <div key={index} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                      <div className={`max-w-[80%] p-3 rounded-lg ${
                        msg.role === 'user' 
                          ? 'bg-[#7A3B48] text-white' 
                          : 'bg-[#4A4A4A] text-gray-200'
                      }`}>
                        <p className="text-sm">{msg.content}</p>
                      </div>
                    </div>
                  ))}
                  <div ref={conversationEndRef} />
                </div>
              )}
            </div>

            {/* Chat Input */}
            <div className="space-y-3">
              <div className="flex gap-2">
                <Textarea
                  value={chatInput}
                  onChange={(e) => setChatInput(e.target.value)}
                  placeholder="Buraya yazın"
                  className="flex-1 bg-[#2E2A2B] border-gray-600 text-gray-200 placeholder-gray-400"
                  rows={3}
                  onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && send(true)}
                />
                <Button 
                  className="bg-[#7A3B48] hover:bg-[#96394A] text-white px-6"
                  onClick={() => send(true)}
                  disabled={loading || !chatInput.trim()}
                >
                  {loading ? (
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                  ) : (
                    <Send className="w-4 h-4" />
                  )}
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function AdminPage() {
  const { darkMode } = useAuth();
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-[#E8C5C9]">Admin Paneli</h1>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="bg-[#3C2C34] border-[#7A3B48]/30">
          <CardContent className="p-6">
            <div className="flex items-center">
              <Users className="w-8 h-8 text-[#B14556] mr-3" />
              <div>
                <h3 className="text-lg font-semibold text-[#E8C5C9]">Kullanıcılar</h3>
                <p className="text-gray-300 text-sm">Toplam kullanıcı sayısı</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[#3C2C34] border-[#7A3B48]/30">
          <CardContent className="p-6">
            <div className="flex items-center">
              <FileText className="w-8 h-8 text-[#B14556] mr-3" />
              <div>
                <h3 className="text-lg font-semibold text-[#E8C5C9]">Dokümanlar</h3>
                <p className="text-gray-300 text-sm">İşlenen belge sayısı</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[#3C2C34] border-[#7A3B48]/30">
          <CardContent className="p-6">
            <div className="flex items-center">
              <TrendingUp className="w-8 h-8 text-[#B14556] mr-3" />
              <div>
                <h3 className="text-lg font-semibold text-[#E8C5C9]">İstatistikler</h3>
                <p className="text-gray-300 text-sm">Sistem performansı</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

export { AuthContext };
