import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import Card from '../../components/Card';
import Button from '../../components/Button';
import Modal from '../../components/Modal';
import { formatCurrency } from '../../utils/emiCalculator';

const AdminDashboard = () => {
  const { usersList, products, scoringRules, auditLogs, addLoanProduct, updateScoringRule } = useAuth();
  const [activeTab, setActiveTab] = useState('USERS'); // USERS | PRODUCTS | RULES | AUDIT

  // Add Product Modal State
  const [isAddProductOpen, setIsAddProductOpen] = useState(false);
  const [newProduct, setNewProduct] = useState({
    name: '',
    category: 'Unsecured',
    minAmount: '50000',
    maxAmount: '1000000',
    interestRate: '10.5',
    minTenure: '12',
    maxTenure: '60',
    minIncome: '25000',
    eligibility: 'Salaried employees'
  });

  // Edit Rule Modal State
  const [editingRule, setEditingRule] = useState(null);
  const [ruleValue, setRuleValue] = useState('');

  const handleCreateProduct = async (e) => {
    e.preventDefault();
    try {
      await addLoanProduct({
        name: newProduct.name,
        category: newProduct.category,
        minAmount: newProduct.minAmount,
        maxAmount: newProduct.maxAmount,
        interestRate: newProduct.interestRate,
        minTenure: newProduct.minTenure,
        maxTenure: newProduct.maxTenure,
        minIncome: newProduct.minIncome,
        eligibility: newProduct.eligibility
      });
      setIsAddProductOpen(false);
      setNewProduct({
        name: '',
        category: 'Unsecured',
        minAmount: '50000',
        maxAmount: '1000000',
        interestRate: '10.5',
        minTenure: '12',
        maxTenure: '60',
        minIncome: '25000',
        eligibility: 'Salaried employees'
      });
    } catch (err) {
      alert(err.message || 'Could not create the product.');
    }
  };

  const handleSaveRule = () => {
    if (editingRule) {
      updateScoringRule(editingRule.id, ruleValue);
      setEditingRule(null);
    }
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Platform Administration Panel</h1>
          <p className="page-subtitle">Configure system users, loan products, scoring rules, and view audit trails.</p>
        </div>
      </div>

      {/* ADMIN TABS NAVIGATION */}
      <div style={{
        display: 'flex',
        gap: '8px',
        marginBottom: '20px',
        borderBottom: '1px solid var(--border-color)',
        paddingBottom: '8px'
      }}>
        {[
          { key: 'USERS', label: '👥 User Management', count: usersList.length },
          { key: 'PRODUCTS', label: '💳 Loan Products', count: products.length },
          { key: 'RULES', label: '⚙️ Scoring Rules UI', count: scoringRules.length },
          { key: 'AUDIT', label: '📜 Audit Logs', count: auditLogs.length }
        ].map((tab) => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            style={{
              padding: '8px 16px',
              borderRadius: '6px',
              fontSize: '13px',
              fontWeight: activeTab === tab.key ? 700 : 500,
              border: 'none',
              backgroundColor: activeTab === tab.key ? 'var(--primary)' : 'transparent',
              color: activeTab === tab.key ? '#ffffff' : 'var(--text-main)',
              cursor: 'pointer'
            }}
          >
            {tab.label} ({tab.count})
          </button>
        ))}
      </div>

      {/* TAB 1: USERS MANAGEMENT */}
      {activeTab === 'USERS' && (
        <Card title="System Users Registry">
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>User ID</th>
                  <th>Full Name</th>
                  <th>Email Address</th>
                  <th>Assigned Role</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {usersList.map((usr) => (
                  <tr key={usr.id}>
                    <td style={{ fontFamily: 'monospace' }}>{usr.id}</td>
                    <td><strong>{usr.name}</strong></td>
                    <td>{usr.email}</td>
                    <td>
                      <span style={{
                        fontSize: '11px',
                        fontWeight: 700,
                        padding: '2px 8px',
                        borderRadius: '4px',
                        backgroundColor: 'var(--primary-light)',
                        color: 'var(--primary)'
                      }}>
                        {usr.role}
                      </span>
                    </td>
                    <td>
                      <span style={{ color: 'var(--color-approved)', fontWeight: 700, fontSize: '11px' }}>
                        ✓ {usr.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* TAB 2: LOAN PRODUCTS MANAGEMENT */}
      {activeTab === 'PRODUCTS' && (
        <Card
          title="Loan Products Configuration"
          action={
            <Button variant="primary" style={{ fontSize: '12px' }} onClick={() => setIsAddProductOpen(true)}>
              ➕ Add New Product
            </Button>
          }
        >
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Product Name</th>
                  <th>Category</th>
                  <th>Interest Rate</th>
                  <th>Amount Range</th>
                  <th>Tenure Range</th>
                  <th>Min Income</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {products.map((prod) => (
                  <tr key={prod.id}>
                    <td><strong>{prod.name}</strong></td>
                    <td>{prod.category}</td>
                    <td style={{ fontWeight: 700 }}>{prod.interestRate}% p.a.</td>
                    <td>{formatCurrency(prod.minAmount)} – {formatCurrency(prod.maxAmount)}</td>
                    <td>{prod.minTenure} – {prod.maxTenure} mos</td>
                    <td>{formatCurrency(prod.minIncome)}</td>
                    <td>
                      <span style={{ color: 'var(--color-approved)', fontWeight: 700, fontSize: '11px' }}>
                        ✓ {prod.status}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* TAB 3: SCORING RULES INTERFACE */}
      {activeTab === 'RULES' && (
        <Card title="Credit Assessment Scoring Rules (UI Parameter Config)">
          <p style={{ fontSize: '12px', color: 'var(--text-muted)', marginBottom: '16px' }}>
            Configure credit policy evaluation thresholds. Parameters will be passed to the backend scoring engine REST API.
          </p>
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Rule ID</th>
                  <th>Policy Rule Name</th>
                  <th>Metric Unit</th>
                  <th>Threshold Value</th>
                  <th>Status</th>
                  <th style={{ textAlign: 'right' }}>Action</th>
                </tr>
              </thead>
              <tbody>
                {scoringRules.map((rule) => (
                  <tr key={rule.id}>
                    <td style={{ fontFamily: 'monospace' }}>{rule.id}</td>
                    <td><strong>{rule.name}</strong></td>
                    <td>{rule.metric}</td>
                    <td style={{ fontWeight: 700, color: 'var(--primary)' }}>{rule.value}</td>
                    <td>
                      <span style={{ color: 'var(--color-approved)', fontWeight: 700, fontSize: '11px' }}>
                        ✓ {rule.status}
                      </span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      <Button
                        variant="secondary"
                        style={{ padding: '2px 8px', fontSize: '11px' }}
                        onClick={() => {
                          setEditingRule(rule);
                          setRuleValue(rule.value);
                        }}
                      >
                        Edit Value
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* TAB 4: AUDIT LOGS */}
      {activeTab === 'AUDIT' && (
        <Card title="System Activity & Assessment Audit Trail">
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Log ID</th>
                  <th>Application Ref</th>
                  <th>Actor / System Role</th>
                  <th>Action Performed</th>
                  <th>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {auditLogs.map((log) => (
                  <tr key={log.id}>
                    <td style={{ fontFamily: 'monospace' }}>{log.id}</td>
                    <td style={{ fontFamily: 'monospace', fontWeight: 700, color: 'var(--primary)' }}>{log.applicationId}</td>
                    <td>{log.actor}</td>
                    <td>
                      <span style={{
                        fontSize: '11px',
                        fontWeight: 700,
                        padding: '2px 8px',
                        borderRadius: '4px',
                        backgroundColor: 'var(--bg-subtle)',
                        border: '1px solid var(--border-color)'
                      }}>
                        {log.action}
                      </span>
                    </td>
                    <td style={{ fontSize: '12px', color: 'var(--text-muted)' }}>
                      {new Date(log.timestamp).toLocaleString('en-IN')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}

      {/* ADD LOAN PRODUCT MODAL */}
      <Modal
        isOpen={isAddProductOpen}
        onClose={() => setIsAddProductOpen(false)}
        title="Add New Loan Product"
      >
        <form onSubmit={handleCreateProduct}>
          <div className="form-group">
            <label className="form-label">Product Name</label>
            <input
              type="text"
              className="form-control"
              required
              value={newProduct.name}
              onChange={(e) => setNewProduct({ ...newProduct, name: e.target.value })}
            />
          </div>

          <div className="grid-2">
            <div className="form-group">
              <label className="form-label">Interest Rate (% p.a.)</label>
              <input
                type="number"
                step="0.1"
                className="form-control"
                required
                value={newProduct.interestRate}
                onChange={(e) => setNewProduct({ ...newProduct, interestRate: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Category</label>
              <select
                className="form-control"
                value={newProduct.category}
                onChange={(e) => setNewProduct({ ...newProduct, category: e.target.value })}
              >
                <option value="Unsecured">Unsecured</option>
                <option value="Secured">Secured</option>
              </select>
            </div>

            <div className="form-group">
              <label className="form-label">Min Amount (₹)</label>
              <input
                type="number"
                className="form-control"
                required
                value={newProduct.minAmount}
                onChange={(e) => setNewProduct({ ...newProduct, minAmount: e.target.value })}
              />
            </div>

            <div className="form-group">
              <label className="form-label">Max Amount (₹)</label>
              <input
                type="number"
                className="form-control"
                required
                value={newProduct.maxAmount}
                onChange={(e) => setNewProduct({ ...newProduct, maxAmount: e.target.value })}
              />
            </div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '16px' }}>
            <Button variant="secondary" onClick={() => setIsAddProductOpen(false)}>Cancel</Button>
            <Button type="submit" variant="primary">Create Product</Button>
          </div>
        </form>
      </Modal>

      {/* EDIT SCORING RULE MODAL */}
      <Modal
        isOpen={!!editingRule}
        onClose={() => setEditingRule(null)}
        title={`Edit Threshold: ${editingRule?.name}`}
        footer={
          <>
            <Button variant="secondary" onClick={() => setEditingRule(null)}>Cancel</Button>
            <Button variant="primary" onClick={handleSaveRule}>Save Rule Parameter</Button>
          </>
        }
      >
        <p style={{ fontSize: '13px', color: 'var(--text-muted)' }}>
          Update policy threshold value for <strong>{editingRule?.name}</strong>:
        </p>
        <div className="form-group" style={{ marginTop: '12px' }}>
          <label className="form-label">Threshold Value ({editingRule?.metric})</label>
          <input
            type="text"
            className="form-control"
            value={ruleValue}
            onChange={(e) => setRuleValue(e.target.value)}
          />
        </div>
      </Modal>
    </div>
  );
};

export default AdminDashboard;
