import { useEffect, useState } from "react";
import { api } from "../services/api";
import type { CreditTransaction } from "../types";

export default function CreditHistory() {
  const [transactions, setTransactions] = useState<CreditTransaction[]>([]);

  useEffect(() => {
    api.get<CreditTransaction[]>("/me/credits/history").then(setTransactions);
  }, []);

  return (
    <div className="page">
      <div className="card">
        <h1>Credit History</h1>
        <table>
          <thead>
            <tr>
              <th>Date</th>
              <th>Type</th>
              <th>Amount</th>
              <th>Description</th>
            </tr>
          </thead>
          <tbody>
            {transactions.map((t) => (
              <tr key={t.id}>
                <td>{new Date(t.created_at).toLocaleString()}</td>
                <td>{t.transaction_type}</td>
                <td>{t.amount > 0 ? `+${t.amount}` : t.amount}</td>
                <td>{t.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
