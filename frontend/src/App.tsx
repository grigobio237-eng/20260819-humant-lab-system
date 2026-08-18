import { useState, useEffect } from 'react';

function App() {
  const [bids, setBids] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchBids = async () => {
    setLoading(true);
    try {
      const response = await fetch('https://db.gleemile.com/api/v1/bids');
      const data = await response.json();
      setBids(data);
    } catch (error) {
      console.error("Failed to fetch bids:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchBids();
  }, []);

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('ko-KR', { style: 'currency', currency: 'KRW' }).format(amount);
  };

  return (
    <div className="min-h-screen p-8 bg-gray-50">
      <header className="mb-8 flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold text-gray-800">휴먼트 랩 시스템 대시보드</h1>
          <p className="text-gray-500 mt-2">최적 사정률 기반 투찰가 자동 계산 및 적격심사 관리 (DB 실시간 연동)</p>
        </div>
        <button 
          onClick={fetchBids}
          className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700 transition"
        >
          {loading ? '동기화 중...' : '새로고침 (API Sync)'}
        </button>
      </header>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-100">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">상태</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">공고번호</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">공고명 / 발주처</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">기초금액 (범위)</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">추천 사정률</th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">최종 투찰가</th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">적격심사</th>
              <th className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">액션</th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {bids.length === 0 && (
              <tr>
                <td colSpan={8} className="px-6 py-8 text-center text-gray-500">
                  수집된 입찰 공고가 없습니다. 백엔드(n8n)를 통해 데이터를 입력해 주세요.
                </td>
              </tr>
            )}
            {bids.map((bid) => (
              <tr key={bid.bid_full_no} className="hover:bg-gray-50 transition">
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                    bid.status === 'PENDING' ? 'bg-yellow-100 text-yellow-800' : 'bg-green-100 text-green-800'
                  }`}>
                    {bid.status === 'PENDING' ? '검토 대기' : '검토 완료'}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {bid.bid_full_no}
                </td>
                <td className="px-6 py-4">
                  <div className="text-sm font-medium text-gray-900 line-clamp-1">{bid.bid_name}</div>
                  <div className="text-sm text-gray-500">{bid.client_name}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900">{formatCurrency(bid.base_price)}</div>
                  <div className="text-xs text-gray-500">{bid.range}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-bold text-blue-600">{bid.recommended_est_rate}%</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm font-bold text-gray-900">
                  {formatCurrency(bid.calculated_bid_price)}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-center">
                  {bid.is_qualified ? (
                    <span className="text-green-600 font-bold">통과(O)</span>
                  ) : (
                    <span className="text-red-500 font-bold">미달(X)</span>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                  <button className="text-indigo-600 hover:text-indigo-900 bg-indigo-50 px-3 py-1 rounded">
                    상세 및 투찰
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default App;
