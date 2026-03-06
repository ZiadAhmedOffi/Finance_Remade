import React, { useState, useEffect } from "react";
import { api } from "../api/api";

interface AdminFeeData {
  total_admin_cost: number;
  operations_fee: number;
  management_fees: number;
  total_costs: number;
}

interface PerformanceData {
  admin_fee: AdminFeeData;
}

interface AdminFeeTabProps {
  fundId: string;
}

const AdminFeeTab: React.FC<AdminFeeTabProps> = ({ fundId }) => {
  const [data, setData] = useState<PerformanceData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPerformance = async () => {
      try {
        setLoading(true);
        const response = await api.get(`/funds/${fundId}/performance/`);
        setData(response.data);
      } catch (err) {
        setError("Failed to fetch admin fee data.");
      } finally {
        setLoading(false);
      }
    };
    fetchPerformance();
  }, [fundId]);

  if (loading) return <div>Loading Admin Fee Data...</div>;
  if (error) return <div className="error-state">{error}</div>;
  if (!data) return null;

  const { admin_fee } = data;

  const formatCurrency = (val: number) => 
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(val);

  return (
    <section className="admin-fee-tab">
      <div className="total-costs-table-container">
        <h3>Total Fund Costs</h3>
        <table className="total-costs-table">
          <thead>
            <tr>
              <th>Description</th>
              <th>Total (USD)</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>Total Admin Cost</td>
              <td>{formatCurrency(admin_fee.total_admin_cost)}</td>
            </tr>
            <tr>
              <td>Operations Fee</td>
              <td>{formatCurrency(admin_fee.operations_fee)}</td>
            </tr>
            <tr>
              <td>Management Fees</td>
              <td>{formatCurrency(admin_fee.management_fees)}</td>
            </tr>
            <tr className="total-row">
              <td><strong>Total Fund Costs</strong></td>
              <td><strong>{formatCurrency(admin_fee.total_costs)}</strong></td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  );
};

export default AdminFeeTab;
