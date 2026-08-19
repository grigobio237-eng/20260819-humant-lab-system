import { useState, useEffect } from 'react';

function App() {
  const [bids, setBids] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  
  // 상태 변수
  const [searchTerm, setSearchTerm] = useState('');
  const [showOnlyQualified, setShowOnlyQualified] = useState(false);
  const [selectedBid, setSelectedBid] = useState<any | null>(null);
  const [copyFeedback, setCopyFeedback] = useState(false);

  // 회사 관리 상태
  const [companies, setCompanies] = useState<any[]>([]);
  const [selectedCompanyId, setSelectedCompanyId] = useState<number | ''>('');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  
  // 회사 관리 폼 상태
  const [editingCompany, setEditingCompany] = useState<any | null>(null);
  const [formData, setFormData] = useState({
    company_name: '',
    business_reg_no: '',
    region_code: '',
    licenses: {} as Record<string, number>
  });
  const [newLicenseName, setNewLicenseName] = useState('');
  const [newLicenseLimit, setNewLicenseLimit] = useState('');

  // --- API 호출 함수 ---
  const fetchCompanies = async () => {
    try {
      const res = await fetch('https://db.gleemile.com/api/v1/companies');
      const data = await res.json();
      setCompanies(data);
      // 만약 선택된 회사가 없고 등록된 회사가 있다면 첫 번째 회사 자동 선택
      if (!selectedCompanyId && data.length > 0) {
        setSelectedCompanyId(data[0].id);
      }
    } catch (error) {
      console.error("Failed to fetch companies:", error);
    }
  };

  const fetchBids = async () => {
    setLoading(true);
    try {
      const url = selectedCompanyId 
        ? `https://db.gleemile.com/api/v1/bids?company_id=${selectedCompanyId}`
        : 'https://db.gleemile.com/api/v1/bids';
      const response = await fetch(url);
      const data = await response.json();
      setBids(data);
    } catch (error) {
      console.error("Failed to fetch bids:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCompanies();
  }, []);

  useEffect(() => {
    fetchBids();
  }, [selectedCompanyId]);

  // --- 회사 관리 CRUD ---
  const saveCompany = async () => {
    const method = editingCompany ? 'PUT' : 'POST';
    const url = editingCompany 
      ? `https://db.gleemile.com/api/v1/companies/${editingCompany.id}`
      : 'https://db.gleemile.com/api/v1/companies';
      
    try {
      await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(formData)
      });
      await fetchCompanies();
      setEditingCompany(null);
      resetForm();
    } catch (err) {
      alert("저장 실패!");
    }
  };

  const deleteCompany = async (id: number) => {
    if(!confirm("정말 이 회사를 삭제하시겠습니까?")) return;
    try {
      await fetch(`https://db.gleemile.com/api/v1/companies/${id}`, { method: 'DELETE' });
      if (selectedCompanyId === id) setSelectedCompanyId('');
      await fetchCompanies();
    } catch (err) {
      alert("삭제 실패!");
    }
  };

  const resetForm = () => {
    setFormData({ company_name: '', business_reg_no: '', region_code: '', licenses: {} });
  };

  const openEdit = (comp: any) => {
    setEditingCompany(comp);
    setFormData({
      company_name: comp.company_name,
      business_reg_no: comp.business_reg_no,
      region_code: comp.region_code || '',
      licenses: comp.licenses || {}
    });
  };

  const addLicense = () => {
    if (!newLicenseName || !newLicenseLimit) return;
    setFormData({
      ...formData,
      licenses: { ...formData.licenses, [newLicenseName]: Number(newLicenseLimit) }
    });
    setNewLicenseName('');
    setNewLicenseLimit('');
  };

  const removeLicense = (name: string) => {
    const newLicenses = { ...formData.licenses };
    delete newLicenses[name];
    setFormData({ ...formData, licenses: newLicenses });
  };

  // --- 포맷팅 등 유틸 ---
  const formatCurrency = (amount: number | undefined) => {
    if (amount === undefined || amount === null) return '0원';
    return amount.toLocaleString('ko-KR') + '원';
  };

  const handleCopy = (price: number) => {
    navigator.clipboard.writeText(price.toString()).then(() => {
      setCopyFeedback(true);
      setTimeout(() => setCopyFeedback(false), 2000);
    });
  };

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
            <p className="text-gray-500 mt-2">다중 회사 적격심사 실시간 판별 및 AI 몬테카를로 투찰가 분석</p>
          </div>
          
          <div className="flex items-center gap-4">
            {/* 회사 선택 드롭다운 */}
            <div className="flex items-center bg-white border rounded shadow-sm px-3 py-2">
              <span className="text-xl mr-2">🏢</span>
              <select 
                value={selectedCompanyId} 
                onChange={(e) => setSelectedCompanyId(e.target.value ? Number(e.target.value) : '')}
                className="bg-transparent focus:outline-none font-bold text-gray-700 w-48"
              >
                <option value="">-- 회사 선택 (전체 공고) --</option>
                {companies.map(c => (
                  <option key={c.id} value={c.id}>{c.company_name}</option>
                ))}
              </select>
            </div>
            
            <button 
              onClick={() => setIsSettingsOpen(true)}
              className="bg-gray-800 text-white px-4 py-2 rounded shadow hover:bg-gray-900 transition flex items-center gap-2"
            >
              ⚙️ 회사 관리
            </button>
            <button 
              onClick={fetchBids}
              className="bg-blue-600 text-white px-4 py-2 rounded shadow hover:bg-blue-700 transition"
            >
              {loading ? '동기화 중...' : '새로고침 (API Sync)'}
            </button>
          </div>
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
            <span className="text-sm font-medium text-green-800">적격심사 통과(O) 공고만 보기 (선택 회사 기준)</span>
          </label>
        </div>
      </header>

      {/* 공고 리스트 테이블 */}
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
                  {!selectedCompanyId ? (
                    <span className="text-gray-400 text-xs">회사 미선택</span>
                  ) : bid.is_qualified ? (
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

      {/* 1. 상세 투찰 모달 */}
      {selectedBid && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-[100] p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-2xl w-full max-h-[90vh] flex flex-col">
            <div className="p-6 border-b flex justify-between items-start">
              <div>
                <div className="text-sm text-gray-500 mb-1">{selectedBid.client_name}</div>
                <h2 className="text-xl font-bold text-gray-900">{selectedBid.bid_name}</h2>
                <div className="text-sm text-gray-500 mt-2">공고번호: {selectedBid.bid_full_no}</div>
              </div>
              <button 
                onClick={() => { setSelectedBid(null); setCopyFeedback(false); }}
                className="text-gray-400 hover:text-gray-600 text-2xl font-bold leading-none"
              >&times;</button>
            </div>
            
            <div className="p-6 overflow-y-auto bg-gray-50 flex-1">
              {/* 원본 상세 데이터 렌더링 */}
              {selectedBid.raw_data && Object.keys(selectedBid.raw_data).length > 0 && (
                <div className="bg-white border rounded-lg p-6 mb-6 shadow-sm">
                  <h3 className="text-lg font-bold text-gray-800 mb-4 border-b pb-2">공고 상세 정보 (원본)</h3>
                  <div className="grid grid-cols-2 gap-y-3 gap-x-6 text-sm">
                    <div className="flex justify-between border-b pb-1"><span className="text-gray-500">계약방법</span> <span className="font-medium text-right text-gray-900">{selectedBid.raw_data.cntrctCnclsMthdNm || '-'}</span></div>
                    <div className="flex justify-between border-b pb-1"><span className="text-gray-500">낙찰방법</span> <span className="font-medium text-right text-gray-900">{selectedBid.raw_data.scsbidMthdNm || '-'}</span></div>
                    <div className="flex justify-between border-b pb-1"><span className="text-gray-500">공동수급여부</span> <span className="font-medium text-right text-gray-900">{selectedBid.raw_data.cmmnSpldmdAgrmntMthdNm || '-'}</span></div>
                    <div className="flex justify-between border-b pb-1"><span className="text-gray-500">발주기관</span> <span className="font-medium text-right text-gray-900">{selectedBid.raw_data.ntceInsttNm || '-'}</span></div>
                    
                    {/* A값 추출 결과 */}
                    {selectedBid.raw_data.scraped_a_value !== undefined && (
                      <div className="flex flex-col border-b pb-1 col-span-2 mt-2 bg-yellow-50 p-2 rounded">
                        <div className="flex justify-between items-center mb-1">
                          <span className="text-gray-700 font-bold">첨부파일 AI 파싱 데이터</span>
                          <span className={`text-xs px-2 py-1 rounded-full text-white ${selectedBid.raw_data.confidence_level === 'HIGH' ? 'bg-green-500' : 'bg-yellow-500'}`}>
                            신뢰도: {selectedBid.raw_data.confidence_level}
                          </span>
                        </div>
                        <div className="grid grid-cols-2 gap-2 mt-1">
                          <div className="flex justify-between"><span className="text-gray-500">낙찰하한율</span><span className="font-medium">{selectedBid.raw_data.scraped_lower_rate > 0 ? `${(selectedBid.raw_data.scraped_lower_rate * 100).toFixed(3)}%` : '-'}</span></div>
                          <div className="flex justify-between"><span className="text-gray-500">A값 합산금액</span><span className="font-medium">{selectedBid.raw_data.scraped_a_value > 0 ? formatCurrency(selectedBid.raw_data.scraped_a_value) : '0원'}</span></div>
                        </div>
                        {selectedBid.raw_data.a_value_breakdown && Object.keys(selectedBid.raw_data.a_value_breakdown).length > 0 && (
                          <div className="mt-2 pt-2 border-t border-yellow-200 text-xs text-gray-600">
                            <strong>A값 상세내역:</strong> {Object.entries(selectedBid.raw_data.a_value_breakdown).map(([k, v]) => `${k} ${formatCurrency(v as number)}`).join(', ')}
                          </div>
                        )}
                        <a 
                          href={`https://db.gleemile.com/api/v1/bids/${selectedBid.bid_full_no}/download`}
                          className="mt-3 block text-center bg-gray-800 text-white py-2 rounded text-xs hover:bg-gray-700 transition"
                          target="_blank"
                        >
                          📄 원본 공고문 파일 다운로드 (AI 추출 근거 확인)
                        </a>
                      </div>
                    )}

                    <div className="flex flex-col border-b pb-1 col-span-2 mt-2">
                      <span className="text-gray-500 mb-1">참가자격조건 (면허)</span>
                      <span className="font-medium text-gray-900">{selectedBid.raw_data.prtcptQlfCndNm || '공고명 기반 자체 필터링 적용 (원문 상세조회 요망)'}</span>
                    </div>
                    <div className="flex flex-col border-b pb-1 col-span-2">
                      <span className="text-gray-500 mb-1">참가가능지역</span>
                      <span className="font-medium text-gray-900">{selectedBid.raw_data.prtcptPosblRgnNm || selectedBid.raw_data.cnstrtsiteRgnNm || '전국 (또는 공고 상세참조)'}</span>
                    </div>
                  </div>
                </div>
              )}
              
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-6 mb-6">
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

            <div className="p-4 border-t bg-white flex justify-between items-center">
              <div className="text-sm text-gray-500">마감일시: {selectedBid.deadline}</div>
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

      {/* 2. 회사 관리 설정 모달 */}
      {isSettingsOpen && (
        <div className="fixed inset-0 bg-black bg-opacity-60 flex items-center justify-center z-[150] p-4">
          <div className="bg-white rounded-xl shadow-2xl max-w-4xl w-full max-h-[90vh] flex overflow-hidden">
            
            {/* 좌측: 회사 목록 */}
            <div className="w-1/3 bg-gray-50 border-r flex flex-col">
              <div className="p-4 border-b bg-white">
                <h3 className="font-bold text-lg text-gray-800">등록된 회사 목록</h3>
              </div>
              <div className="flex-1 overflow-y-auto p-2">
                {companies.map(c => (
                  <div 
                    key={c.id} 
                    className="p-3 mb-2 bg-white rounded border shadow-sm cursor-pointer hover:border-blue-500 transition group"
                  >
                    <div className="flex justify-between items-start">
                      <div onClick={() => openEdit(c)} className="flex-1">
                        <div className="font-bold text-gray-900">{c.company_name}</div>
                        <div className="text-xs text-gray-500">{c.business_reg_no} / {c.region_code}</div>
                      </div>
                      <button 
                        onClick={() => deleteCompany(c.id)}
                        className="text-red-500 opacity-0 group-hover:opacity-100 hover:text-red-700 px-2"
                      >×</button>
                    </div>
                  </div>
                ))}
              </div>
              <div className="p-4 bg-white border-t">
                <button 
                  onClick={() => { setEditingCompany(null); resetForm(); }}
                  className="w-full bg-indigo-50 text-indigo-700 py-2 rounded font-medium hover:bg-indigo-100"
                >+ 새 회사 추가</button>
              </div>
            </div>

            {/* 우측: 회사 수정/입력 폼 */}
            <div className="w-2/3 flex flex-col bg-white">
              <div className="p-4 border-b flex justify-between items-center">
                <h3 className="font-bold text-lg text-gray-800">
                  {editingCompany ? `'${editingCompany.company_name}' 정보 수정` : '새로운 회사 등록'}
                </h3>
                <button onClick={() => setIsSettingsOpen(false)} className="text-2xl text-gray-400 hover:text-gray-600">&times;</button>
              </div>
              
              <div className="flex-1 overflow-y-auto p-6">
                <div className="grid grid-cols-2 gap-4 mb-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">회사명</label>
                    <input type="text" className="w-full border rounded p-2" 
                      value={formData.company_name} onChange={e => setFormData({...formData, company_name: e.target.value})} />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">사업자번호</label>
                    <input type="text" className="w-full border rounded p-2" 
                      value={formData.business_reg_no} onChange={e => setFormData({...formData, business_reg_no: e.target.value})} />
                  </div>
                  <div className="col-span-2">
                    <label className="block text-sm font-medium text-gray-700 mb-1">본사 소재지 (예: 서울특별시, 경기도)</label>
                    <input type="text" className="w-full border rounded p-2" 
                      value={formData.region_code} onChange={e => setFormData({...formData, region_code: e.target.value})} />
                  </div>
                </div>

                <div className="mb-2">
                  <h4 className="font-bold text-gray-800 border-b pb-2 mb-4">보유 면허 및 시공능력평가액</h4>
                  
                  {/* 추가된 면허 리스트 */}
                  <div className="space-y-2 mb-4">
                    {Object.entries(formData.licenses).map(([name, limit]) => (
                      <div key={name} className="flex justify-between items-center bg-gray-50 p-2 rounded border">
                        <span className="font-medium text-gray-700">{name}</span>
                        <div className="flex items-center gap-4">
                          <span className="text-gray-900 font-bold">{formatCurrency(limit)}</span>
                          <button onClick={() => removeLicense(name)} className="text-red-500 text-sm">삭제</button>
                        </div>
                      </div>
                    ))}
                    {Object.keys(formData.licenses).length === 0 && (
                      <div className="text-sm text-gray-400 text-center py-4">등록된 면허가 없습니다.</div>
                    )}
                  </div>

                  {/* 면허 추가 인풋 */}
                  <div className="flex gap-2 items-end bg-blue-50 p-3 rounded">
                    <div className="flex-1">
                      <label className="block text-xs font-medium text-gray-600 mb-1">면허명 (예: 실내건축공사업)</label>
                      <input type="text" className="w-full border rounded p-1.5 text-sm" 
                        value={newLicenseName} onChange={e => setNewLicenseName(e.target.value)} />
                    </div>
                    <div className="flex-1">
                      <label className="block text-xs font-medium text-gray-600 mb-1">시평액 (숫자만, 예: 3000000000)</label>
                      <input type="number" className="w-full border rounded p-1.5 text-sm" 
                        value={newLicenseLimit} onChange={e => setNewLicenseLimit(e.target.value)} />
                    </div>
                    <button onClick={addLicense} className="bg-blue-600 text-white px-3 py-1.5 rounded text-sm font-medium h-[34px]">추가</button>
                  </div>
                </div>
              </div>

              <div className="p-4 border-t bg-gray-50 flex justify-end gap-2">
                <button onClick={() => setIsSettingsOpen(false)} className="px-4 py-2 bg-white border rounded text-gray-700">닫기</button>
                <button onClick={saveCompany} className="px-4 py-2 bg-blue-600 text-white rounded font-medium hover:bg-blue-700">
                  {editingCompany ? '수정 내용 저장' : '새 회사 등록'}
                </button>
              </div>
            </div>
            
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
