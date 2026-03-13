'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useSellers } from '@/hooks/useSellers';

const MONTHLY_LIMIT = 40;

export default function SellersPage() {
  const { sellers, sellerJobs, loading, createSeller, deleteSeller, getMonthlyJobCount } = useSellers();
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [newSellerName, setNewSellerName] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  const handleCreate = async () => {
    if (!newSellerName.trim()) return;
    setIsCreating(true);
    await createSeller(newSellerName.trim());
    setNewSellerName('');
    setShowCreateForm(false);
    setIsCreating(false);
  };

  const handleDelete = async (id: string) => {
    await deleteSeller(id);
    setDeleteConfirmId(null);
  };

  // Summary stats
  const totalJobsThisMonth = sellers.reduce((sum, s) => sum + getMonthlyJobCount(s.id), 0);
  const totalJobs = sellerJobs.length;

  return (
    <div className="p-6 lg:p-8">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-[#282727]">Seller Management</h1>
          <p className="text-base text-[#939393]">Manage sellers and track their job requests.</p>
        </div>
        <button onClick={() => setShowCreateForm(!showCreateForm)} className="btn-primary text-sm">
          <svg className="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
          </svg>
          New Seller
        </button>
      </div>

      {/* Summary Strip */}
      {sellers.length > 0 && (
        <div className="grid grid-cols-3 gap-3 mb-5">
          <div className="card px-4 py-3">
            <p className="text-xs text-[#939393] mb-0.5">Sellers</p>
            <p className="text-2xl font-bold text-[#282727]">{sellers.length}</p>
          </div>
          <div className="card px-4 py-3">
            <p className="text-xs text-[#939393] mb-0.5">Total Jobs</p>
            <p className="text-2xl font-bold text-[#282727]">{totalJobs}</p>
          </div>
          <div className="card px-4 py-3">
            <p className="text-xs text-[#939393] mb-0.5">This Month</p>
            <p className="text-2xl font-bold text-[#282727]">{totalJobsThisMonth}</p>
          </div>
        </div>
      )}

      {/* Create Seller Form */}
      {showCreateForm && (
        <div className="card p-4 mb-5">
          <h3 className="text-sm font-semibold text-[#282727] mb-2">Create New Seller</h3>
          <div className="flex gap-2">
            <input
              type="text"
              value={newSellerName}
              onChange={(e) => setNewSellerName(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
              placeholder="Seller company name..."
              className="input-field flex-1"
              autoFocus
            />
            <button
              onClick={handleCreate}
              disabled={isCreating || !newSellerName.trim()}
              className={`btn-primary text-sm ${isCreating || !newSellerName.trim() ? 'opacity-50 cursor-not-allowed' : ''}`}
            >
              {isCreating ? 'Creating...' : 'Create'}
            </button>
            <button
              onClick={() => { setShowCreateForm(false); setNewSellerName(''); }}
              className="btn-secondary text-sm"
            >
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="card p-12 text-center">
          <svg className="w-6 h-6 text-[#939393] animate-spin mx-auto mb-2" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <p className="text-xs text-[#939393]">Loading sellers...</p>
        </div>
      )}

      {/* Empty */}
      {!loading && sellers.length === 0 && (
        <div className="card p-12 text-center">
          <div className="w-12 h-12 mx-auto mb-3 rounded-lg bg-slate-100 flex items-center justify-center">
            <svg className="w-6 h-6 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </div>
          <h3 className="text-sm font-semibold text-[#282727] mb-1">No sellers yet</h3>
          <p className="text-xs text-[#939393] max-w-xs mx-auto mb-4">
            Create a seller to start tracking their job requests and analytics.
          </p>
          <button onClick={() => setShowCreateForm(true)} className="btn-primary text-sm">Create First Seller</button>
        </div>
      )}

      {/* Sellers Grid */}
      {!loading && sellers.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
          {sellers.map((seller) => {
            const monthlyCount = getMonthlyJobCount(seller.id);
            const sellerJobsList = sellerJobs.filter((j) => j.seller_id === seller.id);
            const completedCount = sellerJobsList.filter((j) => j.status === 'completed').length;
            const processingCount = sellerJobsList.filter((j) => j.status === 'processing' || j.status === 'pending').length;
            const usagePercent = Math.min((monthlyCount / MONTHLY_LIMIT) * 100, 100);
            const isOverLimit = monthlyCount >= MONTHLY_LIMIT;

            return (
              <div key={seller.id} className="relative group">
                {deleteConfirmId === seller.id && (
                  <div className="absolute inset-0 bg-white/95 rounded-xl z-10 flex flex-col items-center justify-center p-4">
                    <p className="text-xs font-medium text-[#282727] mb-2">Delete {seller.name}?</p>
                    <div className="flex gap-2">
                      <button onClick={() => setDeleteConfirmId(null)} className="px-2.5 py-1 text-xs font-medium text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-md">Cancel</button>
                      <button onClick={() => handleDelete(seller.id)} className="px-2.5 py-1 text-xs font-medium text-white bg-red-500 hover:bg-red-600 rounded-md">Delete</button>
                    </div>
                  </div>
                )}

                <Link href={`/dashboard/sellers/${seller.id}`}>
                  <div className="card p-4 hover:border-slate-300 cursor-pointer transition-all">
                    <button
                      onClick={(e) => { e.preventDefault(); e.stopPropagation(); setDeleteConfirmId(seller.id); }}
                      className="absolute top-2.5 right-2.5 p-1 rounded text-slate-300 hover:text-red-500 hover:bg-red-50 opacity-0 group-hover:opacity-100 transition-all z-[5]"
                    >
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                      </svg>
                    </button>

                    <div className="flex items-center space-x-2.5 mb-3">
                      <div className="w-8 h-8 rounded bg-[#282727] flex items-center justify-center">
                        <span className="text-white font-bold text-sm">{seller.name.charAt(0)}</span>
                      </div>
                      <div className="min-w-0">
                        <h3 className="text-sm font-semibold text-[#282727] truncate">{seller.name}</h3>
                        <p className="text-[11px] text-[#939393]">{sellerJobsList.length} job{sellerJobsList.length !== 1 ? 's' : ''}</p>
                      </div>
                    </div>

                    <div className="mb-3">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-[10px] text-[#939393]">Monthly</span>
                        <span className={`text-[10px] font-semibold ${isOverLimit ? 'text-red-600' : monthlyCount >= 30 ? 'text-amber-600' : 'text-[#282727]'}`}>
                          {monthlyCount}/{MONTHLY_LIMIT}
                        </span>
                      </div>
                      <div className="w-full bg-slate-100 rounded-full h-1.5">
                        <div
                          className={`h-1.5 rounded-full transition-all ${isOverLimit ? 'bg-red-500' : monthlyCount >= 30 ? 'bg-amber-500' : 'bg-[#282727]'}`}
                          style={{ width: `${usagePercent}%` }}
                        />
                      </div>
                    </div>

                    <div className="flex items-center justify-between pt-2 border-t border-slate-100">
                      <div className="flex items-center space-x-2">
                        {processingCount > 0 && (
                          <span className="flex items-center text-[11px] text-blue-600">
                            <span className="w-1.5 h-1.5 rounded-full bg-blue-500 mr-1 animate-pulse" />{processingCount} active
                          </span>
                        )}
                        {completedCount > 0 && (
                          <span className="flex items-center text-[11px] text-emerald-600">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1" />{completedCount} done
                          </span>
                        )}
                        {sellerJobsList.length === 0 && (
                          <span className="text-[11px] text-slate-300">No jobs yet</span>
                        )}
                      </div>
                      <svg className="w-3.5 h-3.5 text-slate-300 group-hover:text-[#282727]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  </div>
                </Link>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
