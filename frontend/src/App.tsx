import { useState, useEffect } from 'react';

function App() {
  const [bids, setBids] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  // 상태 변수 추가: 검색어, 필터, 모달 선택
  const [searchTerm, setSearchTerm] = useState('');
  const [showOnlyQualified, setShowOnlyQualified] = useState(false);
  const [selectedBid, setSelectedBid] = useState<any | null>(null);
  const [copyFeedback, setCopyFeedback] = useState(false);

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

  // 천 단위 콤마와 '원' 붙이기
  const formatCurrency = (amount: number | undefined) => {
    if (amount === undefined || amount === null) return '0원';
    return amount.toLocaleString('ko-KR') + '원';
  };

  // 투찰가 복사 기능
  const handleCopy = (price: number) => {
    navigator.clipboard.writeText(price.toString()).then(() => {
      setCopyFeedback(true);
      setTimeout(() => setCopyFeedback(false), 2000);
    });
  };

  // 필터링 적용
  const filteredBids = bids.filter((bid) => {
    const matchSearch = bid.bid_name.includes(searchTerm) || bid.client_name.includes(searchTerm);
    const matchQualified = showOnlyQualified ? bid.is_qualified === true : true;
    return matchSearch && matchQualified;
  });

  return (
    <div className="min-h-screen p-8 bg-gray-50 relative">
      <header className="mb-8">
        <div className="flex justify-between items-center mb-4">
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
        </div>
        
        {/* 필터 및 검색 바 */}
        <div className="flex gap-4 items-center bg-white p-4 rounded-lg shadow-sm">
          <input 
            type="text" 
            placeholder="공고명 또는 발주처 검색..." 
            className="border p-2 rounded flex-1 focus:outline-none focus:ring-2 focus:ring-blue-500"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
          <label className="flex items-center gap-2 cursor-pointer bg-green-50 px-4 py-2 rounded border border-green-200">
            <input 
              type="checkbox" 
              checked={showOnlyQualified}
              onChange={(e) => setShowOnlyQualified(e.target.checked)}
              className="w-4 h-4 text-green-600"
            />
            <span className="text-sm font-medium text-green-800">적격심사 통과(O) 공고만 보기</span>
          </label>
        </div>
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
            {filteredBids.length === 0 && (
              <tr>
                <td colSpan={8} className="px-6 py-8 text-center text-gray-500">
                  표시할 공고가 없습니다.
                </td>
              </tr>
            )}
            {filteredBids.map((bid) => (
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
                  {bid.is_net_cost_applied && (
                    <div className="mt-1 inline-block bg-orange-100 text-orange-800 text-xs px-2 py-0.5 rounded font-bold">
                      ⚠️ 순공사원가 98% 하한선 적용
                    </div>
                  )}
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900">{formatCurrency(bid.base_price)}</div>
                  <div className="text-xs text-gray-500">{bid.range}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-bold text-blue-600">{(Number(bid.recommended_est_rate) * 100).toFixed(4)}%</div>
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
                  <button 
                    onClick={() => setSelectedBid(bid)}
                    className="text-indigo-600 hover:text-indigo-900 bg-indigo-50 px-3 py-1 rounded hover:bg-indigo-100 transition"
                  >
                    상세 및 투찰
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* 모달 창 */}
      {selectedBid && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] flex flex-col">
            
            {/* 모달 헤더 */}
            <div className="p-6 border-b flex justify-between items-start">
              <div>
                <div className="text-sm text-gray-500 mb-1">{selectedBid.client_name}</div>
                <h2 className="text-xl font-bold text-gray-900">{selectedBid.bid_name}</h2>
                <div className="text-sm text-gray-500 mt-2">공고번호: {selectedBid.bid_full_no}</div>
              </div>
              <button 
                onClick={() => { setSelectedBid(null); setCopyFeedback(false); }}
                className="text-gray-400 hover:text-gray-600 text-2xl font-bold leading-none"
              >
                &times;
              </button>
            </div>

            {/* 모달 내용 */}
            <div className="p-6 overflow-y-auto bg-gray-50 flex-1">
              {/* 경고 뱃지 */}
              {selectedBid.is_net_cost_applied && (
                <div className="mb-6 p-4 bg-orange-100 border-l-4 border-orange-500 text-orange-800 rounded">
                  <p className="font-bold">⚠️ 순공사원가 98% 하한선 방어 적용됨</p>
                  <p className="text-sm mt-1">계산된 투찰가가 순공사원가의 98% 미만으로 떨어져, 법적 하한선으로 자동 보정되었습니다.</p>
                </div>
              )}

              <div className="grid grid-cols-2 gap-6 mb-6">
                <div className="bg-white p-4 rounded shadow-sm border">
                  <div className="text-xs text-gray-500 mb-1">기초금액</div>
                  <div className="text-lg font-bold">{formatCurrency(selectedBid.base_price)}</div>
                </div>
                <div className="bg-white p-4 rounded shadow-sm border">
                  <div className="text-xs text-gray-500 mb-1">A값 (국민연금 등 제외 대상 금액)</div>
                  <div className="text-lg font-bold">{formatCurrency(selectedBid.a_value)}</div>
                </div>
                <div className="bg-white p-4 rounded shadow-sm border">
                  <div className="text-xs text-gray-500 mb-1">순공사원가</div>
                  <div className="text-lg font-bold">{formatCurrency(selectedBid.net_cost)}</div>
                </div>
                <div className="bg-white p-4 rounded shadow-sm border">
                  <div className="text-xs text-gray-500 mb-1">적용 하한율</div>
                  <div className="text-lg font-bold">{selectedBid.lower_rate ? (selectedBid.lower_rate * 100).toFixed(3) : 0}%</div>
                </div>
              </div>

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-6">
                <div className="flex justify-between items-end mb-4">
                  <div>
                    <div className="text-sm text-blue-800 font-medium mb-1">AI 몬테카를로 추천 사정률</div>
                    <div className="text-3xl font-black text-blue-600">{(Number(selectedBid.recommended_est_rate) * 100).toFixed(4)}%</div>
                  </div>
                  <div className="text-right">
                    <div className="text-sm text-blue-800 font-medium mb-1">최종 추천 투찰가</div>
                    <div className="text-3xl font-black text-gray-900">{formatCurrency(selectedBid.calculated_bid_price)}</div>
                  </div>
                </div>
                
                <button 
                  onClick={() => handleCopy(selectedBid.calculated_bid_price)}
                  className={`w-full py-3 rounded-lg font-bold text-lg transition shadow flex items-center justify-center gap-2 ${
                    copyFeedback ? 'bg-green-500 text-white' : 'bg-blue-600 hover:bg-blue-700 text-white'
                  }`}
                >
                  {copyFeedback ? '✅ 투찰가가 클립보드에 복사되었습니다!' : '📋 최종 투찰가 숫자만 복사하기'}
                </button>
              </div>
            </div>

            {/* 모달 푸터 */}
            <div className="p-4 border-t bg-white flex justify-between items-center">
              <div className="text-sm text-gray-500">
                마감일시: {selectedBid.deadline}
              </div>
              <a 
                href={selectedBid.link_url || '#'}
                target="_blank" 
                rel="noopener noreferrer"
                className="text-gray-600 hover:text-gray-900 font-medium px-4 py-2 border rounded hover:bg-gray-50"
              >
                나라장터 공고 바로가기 ↗
              </a>
            </div>
            
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
