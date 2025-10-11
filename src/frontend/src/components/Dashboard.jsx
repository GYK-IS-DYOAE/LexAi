import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Search, 
  FileText, 
  Scale, 
  Clock, 
  TrendingUp, 
  Users,
  MessageSquare,
  BookOpen,
  AlertCircle,
  CheckCircle
} from 'lucide-react';

function Dashboard() {
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [stats, setStats] = useState({
    totalCases: 0,
    totalUsers: 0,
    totalSearches: 0,
    avgResponseTime: 0
  });

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      const response = await axios.get('http://localhost:8000/api/admin/stats');
      setStats(response.data);
    } catch (error) {
      console.error('Stats fetch error:', error);
    }
  };

  const handleSearch = async (e) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setLoading(true);
    setError('');
    setSearchResults([]);

    try {
      const response = await axios.post('http://localhost:8000/api/search', {
        query: searchQuery,
        top_k: 5
      });

      setSearchResults(response.data.results || []);
    } catch (error) {
      setError(error.response?.data?.detail || 'Arama yapılamadı');
    } finally {
      setLoading(false);
    }
  };

  const StatCard = ({ title, value, icon: Icon, color = 'cherry' }) => (
    <div className="card p-6">
      <div className="flex items-center">
        <div className={`p-3 rounded-lg bg-${color}-100 dark:bg-${color}-900`}>
          <Icon className={`h-6 w-6 text-${color}-600 dark:text-${color}-400`} />
        </div>
        <div className="ml-4">
          <p className="text-sm font-medium text-gray-500 dark:text-gray-400">{title}</p>
          <p className="text-2xl font-semibold text-gray-900 dark:text-white">{value}</p>
        </div>
      </div>
    </div>
  );

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Welcome Section */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
          Hoş Geldiniz! 👋
        </h1>
        <p className="text-gray-600 dark:text-gray-400">
          LexAI Main hukuk asistanı ile hukuki sorularınızı analiz edin ve mahkeme kararlarını arayın.
        </p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <StatCard
          title="Toplam Dava"
          value={stats.totalCases.toLocaleString()}
          icon={Scale}
          color="cherry"
        />
        <StatCard
          title="Toplam Kullanıcı"
          value={stats.totalUsers.toLocaleString()}
          icon={Users}
          color="primary"
        />
        <StatCard
          title="Toplam Arama"
          value={stats.totalSearches.toLocaleString()}
          icon={Search}
          color="cherry"
        />
        <StatCard
          title="Ortalama Süre"
          value={`${stats.avgResponseTime}ms`}
          icon={Clock}
          color="primary"
        />
      </div>

      {/* Search Section */}
      <div className="card p-6 mb-8">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-4 flex items-center">
          <Search className="h-5 w-5 mr-2 text-cherry-600" />
          Hukuki Arama
        </h2>
        
        <form onSubmit={handleSearch} className="space-y-4">
          <div className="flex gap-4">
            <div className="flex-1">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Hukuki sorunuzu veya anahtar kelimeleri girin..."
                className="input-field"
                disabled={loading}
              />
            </div>
            <button
              type="submit"
              disabled={loading || !searchQuery.trim()}
              className="btn-primary flex items-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
              ) : (
                <Search className="h-4 w-4" />
              )}
              <span>Ara</span>
            </button>
          </div>
        </form>

        {/* Error Message */}
        {error && (
          <div className="mt-4 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-3">
            <div className="flex items-center">
              <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 mr-2" />
              <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
            </div>
          </div>
        )}

        {/* Search Results */}
        {searchResults.length > 0 && (
          <div className="mt-6">
            <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
              Arama Sonuçları ({searchResults.length})
            </h3>
            <div className="space-y-4">
              {searchResults.map((result, index) => (
                <div key={index} className="border border-gray-200 dark:border-gray-700 rounded-lg p-4 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors duration-200">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-2">
                        {result.dava_turu || 'Mahkeme Kararı'}
                      </h4>
                      <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                        {result.metin_preview}
                      </p>
                      {result.sonuc && (
                        <div className="flex items-center text-xs text-gray-500 dark:text-gray-400">
                          <CheckCircle className="h-3 w-3 mr-1 text-green-500" />
                          Sonuç: {result.sonuc}
                        </div>
                      )}
                    </div>
                    <div className="ml-4 text-right">
                      <div className="text-xs text-gray-500 dark:text-gray-400">
                        Skor: {(result.score * 100).toFixed(1)}%
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="card p-6 hover:shadow-lg transition-shadow duration-200 cursor-pointer">
          <div className="flex items-center mb-4">
            <div className="p-3 rounded-lg bg-cherry-100 dark:bg-cherry-900">
              <FileText className="h-6 w-6 text-cherry-600 dark:text-cherry-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white ml-3">
              Belge Analizi
            </h3>
          </div>
          <p className="text-gray-600 dark:text-gray-400 text-sm">
            Hukuki belgelerinizi yükleyin ve AI ile analiz edin.
          </p>
        </div>

        <div className="card p-6 hover:shadow-lg transition-shadow duration-200 cursor-pointer">
          <div className="flex items-center mb-4">
            <div className="p-3 rounded-lg bg-primary-100 dark:bg-primary-900">
              <MessageSquare className="h-6 w-6 text-primary-600 dark:text-primary-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white ml-3">
              AI Sohbet
            </h3>
          </div>
          <p className="text-gray-600 dark:text-gray-400 text-sm">
            Hukuki sorularınızı AI asistanına sorun.
          </p>
        </div>

        <div className="card p-6 hover:shadow-lg transition-shadow duration-200 cursor-pointer">
          <div className="flex items-center mb-4">
            <div className="p-3 rounded-lg bg-cherry-100 dark:bg-cherry-900">
              <BookOpen className="h-6 w-6 text-cherry-600 dark:text-cherry-400" />
            </div>
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white ml-3">
              Mevzuat Taraması
            </h3>
          </div>
          <p className="text-gray-600 dark:text-gray-400 text-sm">
            Güncel mevzuat ve kanunları tarayın.
          </p>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
