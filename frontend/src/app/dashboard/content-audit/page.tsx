'use client';

import { useEffect, useState, useMemo } from 'react';

interface ContentAuditItem {
  id: number;
  asset_name: string;
  sp_link: string;
  asset_summary: string;
  industry: string;
  service_solution: string;
  year_published: string;
  audience: string;
  format: string;
  page_count: string;
  marketing_or_sales: string;
  consideration: string;
  inventory_recommendations: string;
  audit_notes: string;
  source: 'csv' | 'user';
}

type SortField = 'asset_name' | 'service_solution' | 'year_published' | 'audience' | 'format' | 'inventory_recommendations';
type SortDir = 'asc' | 'desc';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || process.env.NEXT_PUBLIC_API_URL || 'https://radtest-backend-4mux.onrender.com';

export default function ContentAuditPage() {
  const [items, setItems] = useState<ContentAuditItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Sort state
  const [sortField, setSortField] = useState<SortField>('asset_name');
  const [sortDir, setSortDir] = useState<SortDir>('asc');

  // Filter state
  const [searchQuery, setSearchQuery] = useState('');
  const [filterAudience, setFilterAudience] = useState('');
  const [filterSolution, setFilterSolution] = useState('');
  const [filterFormat, setFilterFormat] = useState('');

  // Add-new form state
  const [showAddForm, setShowAddForm] = useState(false);
  const [newItem, setNewItem] = useState({
    asset_name: '',
    sp_link: '',
    asset_summary: '',
    industry: '',
    service_solution: '',
    audience: '',
    format_type: '',
  });
  const [adding, setAdding] = useState(false);

  // Expanded row
  const [expandedId, setExpandedId] = useState<number | null>(null);

  useEffect(() => {
    fetchItems();
  }, []);

  async function fetchItems() {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${BACKEND_URL}/api/content-audit`);
      if (!res.ok) throw new Error(`Failed to load: ${res.status}`);
      const data = await res.json();
      setItems(data.items || []);
    } catch (err: any) {
      setError(err.message || 'Failed to load content audit');
    } finally {
      setLoading(false);
    }
  }

  async function handleAddItem(e: React.FormEvent) {
    e.preventDefault();
    if (!newItem.asset_name.trim() || !newItem.sp_link.trim()) return;
    setAdding(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/content-audit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(newItem),
      });
      if (!res.ok) throw new Error(`Failed to add: ${res.status}`);
      setNewItem({ asset_name: '', sp_link: '', asset_summary: '', industry: '', service_solution: '', audience: '', format_type: '' });
      setShowAddForm(false);
      await fetchItems();
    } catch (err: any) {
      setError(err.message || 'Failed to add item');
    } finally {
      setAdding(false);
    }
  }

  // Derive filter options from data
  const audiences = useMemo(() => [...new Set(items.map(i => i.audience?.trim()).filter(Boolean))].sort(), [items]);
  const solutions = useMemo(() => [...new Set(items.map(i => i.service_solution?.trim()).filter(Boolean))].sort(), [items]);
  const formats = useMemo(() => [...new Set(items.map(i => i.format?.trim()).filter(Boolean))].sort(), [items]);

  // Filter + sort
  const filteredItems = useMemo(() => {
    let result = [...items];

    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(i =>
        i.asset_name?.toLowerCase().includes(q) ||
        i.asset_summary?.toLowerCase().includes(q) ||
        i.service_solution?.toLowerCase().includes(q)
      );
    }
    if (filterAudience) {
      result = result.filter(i => i.audience?.trim() === filterAudience);
    }
    if (filterSolution) {
      result = result.filter(i => i.service_solution?.trim() === filterSolution);
    }
    if (filterFormat) {
      result = result.filter(i => i.format?.trim() === filterFormat);
    }

    result.sort((a, b) => {
      const aVal = (a[sortField] || '').toLowerCase();
      const bVal = (b[sortField] || '').toLowerCase();
      if (aVal < bVal) return sortDir === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDir === 'asc' ? 1 : -1;
      return 0;
    });

    return result;
  }, [items, searchQuery, filterAudience, filterSolution, filterFormat, sortField, sortDir]);

  function handleSort(field: SortField) {
    if (sortField === field) {
      setSortDir(d => d === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDir('asc');
    }
  }

  function SortIcon({ field }: { field: SortField }) {
    if (sortField !== field) return <span className="text-[#939393] ml-1">&#8597;</span>;
    return <span className="text-primary-500 ml-1">{sortDir === 'asc' ? '&#9650;' : '&#9660;'}</span>;
  }

  const recBadge = (rec: string) => {
    const r = rec?.trim().toLowerCase() || '';
    if (r.includes('leverage')) return 'bg-emerald-50 text-emerald-700 border-emerald-200';
    if (r.includes('upcycle')) return 'bg-amber-50 text-amber-700 border-amber-200';
    if (r.includes('retire')) return 'bg-red-50 text-red-700 border-red-200';
    return 'bg-slate-50 text-slate-600 border-slate-200';
  };

  return (
    <div className="p-6 lg:p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-[#282727]">Content Audit</h1>
          <p className="text-base text-[#939393]">HP Canada marketing and sales asset library. Browse, search, and add resources.</p>
        </div>
        <button
          onClick={() => setShowAddForm(v => !v)}
          className="flex items-center gap-2 px-4 py-2.5 bg-[#282727] text-white rounded-lg text-sm font-medium hover:bg-[#1a1a1a] transition-colors"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Add Resource
        </button>
      </div>

      {/* Add Form */}
      {showAddForm && (
        <div className="card mb-6 p-5 border border-primary-200 bg-primary-50/30">
          <h3 className="text-sm font-semibold text-[#282727] mb-4">Add New Resource</h3>
          <form onSubmit={handleAddItem} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-xs font-medium text-[#939393] mb-1">Title *</label>
                <input
                  type="text"
                  value={newItem.asset_name}
                  onChange={e => setNewItem(v => ({ ...v, asset_name: e.target.value }))}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  placeholder="Asset title"
                  required
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#939393] mb-1">Link / URL *</label>
                <input
                  type="text"
                  value={newItem.sp_link}
                  onChange={e => setNewItem(v => ({ ...v, sp_link: e.target.value }))}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                  placeholder="https://..."
                  required
                />
              </div>
            </div>
            <div>
              <label className="block text-xs font-medium text-[#939393] mb-1">Description</label>
              <textarea
                value={newItem.asset_summary}
                onChange={e => setNewItem(v => ({ ...v, asset_summary: e.target.value }))}
                className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                placeholder="Brief description of the resource"
                rows={2}
              />
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div>
                <label className="block text-xs font-medium text-[#939393] mb-1">Industry</label>
                <input
                  type="text"
                  value={newItem.industry}
                  onChange={e => setNewItem(v => ({ ...v, industry: e.target.value }))}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm"
                  placeholder="e.g. Technology"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#939393] mb-1">Service / Solution</label>
                <input
                  type="text"
                  value={newItem.service_solution}
                  onChange={e => setNewItem(v => ({ ...v, service_solution: e.target.value }))}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm"
                  placeholder="e.g. HP Z"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#939393] mb-1">Audience</label>
                <input
                  type="text"
                  value={newItem.audience}
                  onChange={e => setNewItem(v => ({ ...v, audience: e.target.value }))}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm"
                  placeholder="e.g. ITDM"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-[#939393] mb-1">Format</label>
                <input
                  type="text"
                  value={newItem.format_type}
                  onChange={e => setNewItem(v => ({ ...v, format_type: e.target.value }))}
                  className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm"
                  placeholder="e.g. Guide"
                />
              </div>
            </div>
            <div className="flex items-center gap-3 pt-1">
              <button
                type="submit"
                disabled={adding}
                className="px-4 py-2 bg-[#282727] text-white rounded-lg text-sm font-medium hover:bg-[#1a1a1a] disabled:opacity-50 transition-colors"
              >
                {adding ? 'Adding...' : 'Add Resource'}
              </button>
              <button
                type="button"
                onClick={() => setShowAddForm(false)}
                className="px-4 py-2 text-[#939393] hover:text-[#282727] text-sm transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="card px-5 py-3.5">
          <p className="text-sm text-[#939393] mb-0.5">Total Assets</p>
          <p className="text-3xl font-bold text-[#282727]">{items.length}</p>
        </div>
        <div className="card px-5 py-3.5">
          <p className="text-sm text-[#939393] mb-0.5">Leverage</p>
          <p className="text-3xl font-bold text-emerald-600">{items.filter(i => i.inventory_recommendations?.trim().toLowerCase().includes('leverage')).length}</p>
        </div>
        <div className="card px-5 py-3.5">
          <p className="text-sm text-[#939393] mb-0.5">Upcycle</p>
          <p className="text-3xl font-bold text-amber-600">{items.filter(i => i.inventory_recommendations?.trim().toLowerCase().includes('upcycle')).length}</p>
        </div>
        <div className="card px-5 py-3.5">
          <p className="text-sm text-[#939393] mb-0.5">Showing</p>
          <p className="text-3xl font-bold text-[#282727]">{filteredItems.length}</p>
        </div>
      </div>

      {/* Filters */}
      <div className="card p-4 mb-6">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex-1 min-w-[200px]">
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              placeholder="Search assets by name, description, or solution..."
            />
          </div>
          <select
            value={filterAudience}
            onChange={e => setFilterAudience(e.target.value)}
            className="px-3 py-2 border border-slate-200 rounded-lg text-sm bg-white"
          >
            <option value="">All Audiences</option>
            {audiences.map(a => <option key={a} value={a}>{a}</option>)}
          </select>
          <select
            value={filterSolution}
            onChange={e => setFilterSolution(e.target.value)}
            className="px-3 py-2 border border-slate-200 rounded-lg text-sm bg-white"
          >
            <option value="">All Solutions</option>
            {solutions.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
          <select
            value={filterFormat}
            onChange={e => setFilterFormat(e.target.value)}
            className="px-3 py-2 border border-slate-200 rounded-lg text-sm bg-white"
          >
            <option value="">All Formats</option>
            {formats.map(f => <option key={f} value={f}>{f}</option>)}
          </select>
          {(searchQuery || filterAudience || filterSolution || filterFormat) && (
            <button
              onClick={() => { setSearchQuery(''); setFilterAudience(''); setFilterSolution(''); setFilterFormat(''); }}
              className="text-xs text-[#939393] hover:text-[#282727] underline"
            >
              Clear filters
            </button>
          )}
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{error}</div>
      )}

      {/* Table */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <svg className="w-8 h-8 text-[#939393] animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
        </div>
      ) : (
        <div className="card overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100 bg-slate-50/50">
                  <th className="text-left px-4 py-3 font-semibold text-[#282727] cursor-pointer hover:bg-slate-100 transition-colors" onClick={() => handleSort('asset_name')}>
                    Asset Name <SortIcon field="asset_name" />
                  </th>
                  <th className="text-left px-4 py-3 font-semibold text-[#282727] cursor-pointer hover:bg-slate-100 transition-colors w-32" onClick={() => handleSort('service_solution')}>
                    Solution <SortIcon field="service_solution" />
                  </th>
                  <th className="text-left px-4 py-3 font-semibold text-[#282727] cursor-pointer hover:bg-slate-100 transition-colors w-20" onClick={() => handleSort('year_published')}>
                    Year <SortIcon field="year_published" />
                  </th>
                  <th className="text-left px-4 py-3 font-semibold text-[#282727] cursor-pointer hover:bg-slate-100 transition-colors w-24" onClick={() => handleSort('audience')}>
                    Audience <SortIcon field="audience" />
                  </th>
                  <th className="text-left px-4 py-3 font-semibold text-[#282727] cursor-pointer hover:bg-slate-100 transition-colors w-28" onClick={() => handleSort('format')}>
                    Format <SortIcon field="format" />
                  </th>
                  <th className="text-left px-4 py-3 font-semibold text-[#282727] cursor-pointer hover:bg-slate-100 transition-colors w-28" onClick={() => handleSort('inventory_recommendations')}>
                    Status <SortIcon field="inventory_recommendations" />
                  </th>
                  <th className="text-left px-4 py-3 font-semibold text-[#282727] w-20">Link</th>
                </tr>
              </thead>
              <tbody>
                {filteredItems.map((item) => (
                  <>
                    <tr
                      key={item.id}
                      className={`border-b border-slate-50 hover:bg-slate-50/50 cursor-pointer transition-colors ${expandedId === item.id ? 'bg-slate-50' : ''}`}
                      onClick={() => setExpandedId(expandedId === item.id ? null : item.id)}
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-2">
                          {item.source === 'user' && (
                            <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-primary-50 text-primary-600 border border-primary-200">
                              Custom
                            </span>
                          )}
                          <span className="font-medium text-[#282727]">{item.asset_name}</span>
                        </div>
                      </td>
                      <td className="px-4 py-3 text-[#939393]">{item.service_solution}</td>
                      <td className="px-4 py-3 text-[#939393]">{item.year_published}</td>
                      <td className="px-4 py-3">
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-600">
                          {item.audience}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-[#939393]">{item.format}</td>
                      <td className="px-4 py-3">
                        <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${recBadge(item.inventory_recommendations)}`}>
                          {item.inventory_recommendations?.trim() || '-'}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {item.sp_link && (
                          <a
                            href={item.sp_link.startsWith('http') ? item.sp_link : '#'}
                            target="_blank"
                            rel="noopener noreferrer"
                            onClick={e => e.stopPropagation()}
                            className="text-primary-500 hover:text-primary-700 text-xs font-medium"
                          >
                            {item.sp_link.startsWith('http') ? 'Open' : item.sp_link}
                          </a>
                        )}
                      </td>
                    </tr>
                    {expandedId === item.id && (
                      <tr key={`${item.id}-detail`} className="bg-slate-50/80">
                        <td colSpan={7} className="px-6 py-4">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
                            <div>
                              <p className="text-xs font-semibold text-[#939393] uppercase tracking-wide mb-1">Summary</p>
                              <p className="text-[#282727] leading-relaxed">{item.asset_summary || 'No summary available.'}</p>
                            </div>
                            <div className="space-y-2">
                              <div>
                                <p className="text-xs font-semibold text-[#939393] uppercase tracking-wide mb-1">Details</p>
                                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
                                  <span className="text-[#939393]">Industry:</span>
                                  <span className="text-[#282727]">{item.industry || '-'}</span>
                                  <span className="text-[#939393]">Page Count:</span>
                                  <span className="text-[#282727]">{item.page_count || '-'}</span>
                                  <span className="text-[#939393]">Type:</span>
                                  <span className="text-[#282727]">{item.marketing_or_sales || '-'}</span>
                                  <span className="text-[#939393]">Stage:</span>
                                  <span className="text-[#282727]">{item.consideration || '-'}</span>
                                </div>
                              </div>
                              {item.audit_notes && (
                                <div>
                                  <p className="text-xs font-semibold text-[#939393] uppercase tracking-wide mb-1">Audit Notes</p>
                                  <p className="text-[#282727] text-xs leading-relaxed">{item.audit_notes}</p>
                                </div>
                              )}
                            </div>
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
                {filteredItems.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-12 text-center text-[#939393]">
                      {items.length === 0 ? 'No content audit data available.' : 'No assets match your filters.'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
