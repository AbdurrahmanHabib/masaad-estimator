import { create } from 'zustand';

interface EstimateStore {
  boq: any;
  variances: string[];
  status: 'IDLE' | 'INGESTING' | 'ENGINEERING' | 'PRICING' | 'COMPLETE';
  setBOQ: (data: any) => void;
  updateLineItem: (index: number, newRate: number) => void;
}

export const useEstimateStore = create<EstimateStore>((set) => ({
  boq: null,
  variances: [],
  status: 'IDLE',
  setBOQ: (data) => set({ boq: data, status: 'COMPLETE' }),
  updateLineItem: (index, newRate) => set((state: any) => {
    if (!state.boq) return state;
    const newItems = [...state.boq.line_items];
    newItems[index].amount = (newItems[index].quantity || 1) * newRate;
    const newTotal = newItems.reduce((acc: number, item: any) => acc + item.amount, 0);
    return { boq: { ...state.boq, line_items: newItems, total_price_aed: newTotal } };
  }),
}));