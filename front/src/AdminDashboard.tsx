import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { AddStudentModal } from "./components/AddStudentModal";

interface SystemMetrics {
  total_users: number;
  active_users: number;
  total_checkins: number;
  today_checkins: number;
  system_uptime: string;
  database_size: string;
  nfc_reader_status: string;
}

interface User {
  id: number;
  name: string;
  email: string;
  role: string;
  is_active: boolean;
  last_login?: string;
  created_at: string;
}

interface SystemConfig {
  auto_backup_enabled: boolean;
  backup_frequency: string;
  session_timeout: number;
  max_login_attempts: number;
  nfc_scan_timeout: number;
  enable_notifications: boolean;
}

interface AuditLog {
  id: number;
  user_id: number;
  action: string;
  timestamp: string;
  details: string;
  ip_address?: string;
  user_agent?: string;
}

export function AdminDashboard() {
  const navigate = useNavigate();
  const [systemMetrics, setSystemMetrics] = useState<SystemMetrics | null>(
    null
  );
  const [users, setUsers] = useState<User[]>([]);
  const [systemConfig, setSystemConfig] = useState<SystemConfig | null>(null);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);
  const [showConfigModal, setShowConfigModal] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");
  const [showAddStudentModal, setShowAddStudentModal] = useState(false);
  const [newlyCreatedStudentId, setNewlyCreatedStudentId] = useState<
    number | null
  >(null);
  const [isAddingStudent, setIsAddingStudent] = useState(false);

  // Check authentication
  useEffect(() => {
    const token = localStorage.getItem("token");
    const userRole = localStorage.getItem("userRole");

    if (!token || userRole !== "admin") {
      navigate("/login");
      return;
    }

    fetchDashboardData();
  }, [navigate]);

  const fetchDashboardData = async () => {
    try {
      const token = localStorage.getItem("token");
      const headers = {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      };

      // Fetch system metrics
      const metricsResponse = await fetch(
        "http://localhost:8000/admin/system-metrics",
        { headers }
      );
      if (metricsResponse.ok) {
        const metricsData = await metricsResponse.json();
        setSystemMetrics(metricsData);
      }

      // Fetch users
      const usersResponse = await fetch("http://localhost:8000/admin/users", {
        headers,
      });
      if (usersResponse.ok) {
        const usersData = await usersResponse.json();
        setUsers(usersData.users);
      }

      // Fetch system configuration
      const configResponse = await fetch(
        "http://localhost:8000/admin/system-config",
        { headers }
      );
      if (configResponse.ok) {
        const configData = await configResponse.json();
        setSystemConfig(configData);
      }

      // Fetch audit logs
      const logsResponse = await fetch(
        "http://localhost:8000/admin/audit-logs",
        { headers }
      );
      if (logsResponse.ok) {
        const logsData = await logsResponse.json();
        setAuditLogs(logsData.logs);
      }
    } catch {
      setError("Failed to load dashboard data");
    } finally {
      setIsLoading(false);
    }
  };

  const updateUserRole = async (userId: number, newRole: string) => {
    try {
      const token = localStorage.getItem("token");
      const headers = {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      };

      const response = await fetch(
        `http://localhost:8000/admin/users/${userId}/role`,
        {
          method: "PUT",
          headers,
          body: JSON.stringify({ role: newRole }),
        }
      );

      if (response.ok) {
        await fetchDashboardData(); // Refresh data
      } else {
        setError("Failed to update user role");
      }
    } catch {
      setError("Failed to update user role");
    }
  };

  const deleteUser = async (userId: number) => {
    if (
      !confirm(
        "Are you sure you want to delete this user? This action cannot be undone."
      )
    ) {
      return;
    }

    try {
      const token = localStorage.getItem("token");
      const headers = {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      };

      const response = await fetch(
        `http://localhost:8000/admin/users/${userId}`,
        {
          method: "DELETE",
          headers,
        }
      );

      if (response.ok) {
        await fetchDashboardData(); // Refresh data
      } else {
        setError("Failed to delete user");
      }
    } catch {
      setError("Failed to delete user");
    }
  };

  const updateSystemConfig = async () => {
    if (!systemConfig) return;

    try {
      const token = localStorage.getItem("token");
      const headers = {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      };

      const response = await fetch(
        "http://localhost:8000/admin/system-config",
        {
          method: "PUT",
          headers,
          body: JSON.stringify(systemConfig),
        }
      );

      if (response.ok) {
        setShowConfigModal(false);
        await fetchDashboardData(); // Refresh data
      } else {
        setError("Failed to update system configuration");
      }
    } catch {
      setError("Failed to update system configuration");
    }
  };

  // Quick action handlers
  const handleGenerateReport = async () => {
    try {
      setIsLoading(true);
      const token = localStorage.getItem("token");
      const headers = {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      };

      const response = await fetch(
        "http://localhost:8000/admin/generate-report",
        {
          method: "POST",
          headers,
        }
      );

      if (response.ok) {
        const result = await response.json();
        setSuccessMessage(
          `Report generated successfully! Generated at: ${result.report.generated_at}`
        );
        setTimeout(() => setSuccessMessage(""), 5000); // Clear after 5 seconds
      } else {
        setError("Failed to generate report");
      }
    } catch {
      setError("Failed to generate report");
    } finally {
      setIsLoading(false);
    }
  };

  const handleExportData = async () => {
    try {
      setIsLoading(true);
      const token = localStorage.getItem("token");
      const headers = {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      };

      const response = await fetch("http://localhost:8000/admin/export-data", {
        method: "POST",
        headers,
      });

      if (response.ok) {
        const result = await response.json();
        setSuccessMessage(
          `Data exported successfully! Exported at: ${result.data.exported_at}`
        );
        setTimeout(() => setSuccessMessage(""), 5000); // Clear after 5 seconds
      } else {
        setError("Failed to export data");
      }
    } catch {
      setError("Failed to export data");
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateBackup = async () => {
    try {
      setIsLoading(true);
      const token = localStorage.getItem("token");
      const headers = {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      };

      const response = await fetch(
        "http://localhost:8000/admin/create-backup",
        {
          method: "POST",
          headers,
        }
      );

      if (response.ok) {
        const result = await response.json();
        setSuccessMessage(
          `Backup created successfully! Backup ID: ${result.backup.backup_id}`
        );
        setTimeout(() => setSuccessMessage(""), 5000); // Clear after 5 seconds
      } else {
        setError("Failed to create backup");
      }
    } catch {
      setError("Failed to create backup");
    } finally {
      setIsLoading(false);
    }
  };

  const handleMaintenance = async () => {
    try {
      setIsLoading(true);
      const token = localStorage.getItem("token");
      const headers = {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      };

      const response = await fetch("http://localhost:8000/admin/maintenance", {
        method: "POST",
        headers,
      });

      if (response.ok) {
        const result = await response.json();
        setSuccessMessage(
          `Maintenance completed successfully! ${result.tasks.length} tasks completed.`
        );
        setTimeout(() => setSuccessMessage(""), 5000); // Clear after 5 seconds
      } else {
        setError("Failed to perform maintenance");
      }
    } catch {
      setError("Failed to perform maintenance");
    } finally {
      setIsLoading(false);
    }
  };

  const handleEmergencyShutdown = async () => {
    if (
      !confirm(
        "Are you sure you want to initiate emergency shutdown? This action cannot be undone."
      )
    ) {
      return;
    }

    try {
      setIsLoading(true);
      const token = localStorage.getItem("token");
      const headers = {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      };

      const response = await fetch(
        "http://localhost:8000/admin/emergency-shutdown",
        {
          method: "POST",
          headers,
        }
      );

      if (response.ok) {
        const result = await response.json();
        setSuccessMessage(`Emergency shutdown initiated! ${result.message}`);
        setTimeout(() => setSuccessMessage(""), 5000); // Clear after 5 seconds
        // In a real application, you might want to redirect or perform other actions
      } else {
        setError("Failed to initiate emergency shutdown");
      }
    } catch {
      setError("Failed to initiate emergency shutdown");
    } finally {
      setIsLoading(false);
    }
  };

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  const formatDate = (timestamp: string) => {
    return new Date(timestamp).toLocaleDateString();
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-xl">Loading dashboard...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center py-6">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Admin Dashboard
              </h1>
              <p className="mt-1 text-sm text-gray-600">
                NFC Attendance Management System - Full System Administration
              </p>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">
                Welcome, Administrator
              </span>
              <button
                onClick={() => {
                  localStorage.removeItem("token");
                  localStorage.removeItem("userRole");
                  navigate("/login");
                }}
                className="px-4 py-2 text-sm text-white bg-red-600 rounded hover:bg-red-700"
              >
                Logout
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto py-6 sm:px-6 lg:px-8">
        {error && (
          <div className="mb-6 bg-red-50 border border-red-200 text-red-600 px-4 py-3 rounded">
            {error}
          </div>
        )}
        {successMessage && (
          <div className="mb-6 bg-green-50 border border-green-200 text-green-600 px-4 py-3 rounded">
            {successMessage}
          </div>
        )}

        <div className="px-4 py-6 sm:px-0">
          {/* System Metrics */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
            <div className="bg-white shadow rounded-lg p-6">
              <div className="flex items-center">
                <div className="p-3 rounded-full bg-blue-100">
                  <svg
                    className="w-6 h-6 text-blue-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"
                    ></path>
                  </svg>
                </div>
                <div className="ml-4">
                  <h3 className="text-lg font-semibold text-gray-900">
                    Total Users
                  </h3>
                  <p className="text-2xl font-bold text-blue-600">
                    {systemMetrics?.total_users || 0}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white shadow rounded-lg p-6">
              <div className="flex items-center">
                <div className="p-3 rounded-full bg-green-100">
                  <svg
                    className="w-6 h-6 text-green-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                    ></path>
                  </svg>
                </div>
                <div className="ml-4">
                  <h3 className="text-lg font-semibold text-gray-900">
                    Active Users
                  </h3>
                  <p className="text-2xl font-bold text-green-600">
                    {systemMetrics?.active_users || 0}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white shadow rounded-lg p-6">
              <div className="flex items-center">
                <div className="p-3 rounded-full bg-purple-100">
                  <svg
                    className="w-6 h-6 text-purple-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                    ></path>
                  </svg>
                </div>
                <div className="ml-4">
                  <h3 className="text-lg font-semibold text-gray-900">
                    Total Check-ins
                  </h3>
                  <p className="text-2xl font-bold text-purple-600">
                    {systemMetrics?.total_checkins || 0}
                  </p>
                </div>
              </div>
            </div>

            <div className="bg-white shadow rounded-lg p-6">
              <div className="flex items-center">
                <div className="p-3 rounded-full bg-orange-100">
                  <svg
                    className="w-6 h-6 text-orange-600"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                    ></path>
                  </svg>
                </div>
                <div className="ml-4">
                  <h3 className="text-lg font-semibold text-gray-900">
                    Today's Check-ins
                  </h3>
                  <p className="text-2xl font-bold text-orange-600">
                    {systemMetrics?.today_checkins || 0}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* System Status */}
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                System Status
              </h2>
              {systemMetrics ? (
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-sm font-medium text-gray-600">
                      NFC Reader:
                    </span>
                    <span
                      className={`text-sm font-medium ${
                        systemMetrics.nfc_reader_status === "active"
                          ? "text-green-600"
                          : "text-red-600"
                      }`}
                    >
                      {systemMetrics.nfc_reader_status}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-medium text-gray-600">
                      System Uptime:
                    </span>
                    <span className="text-sm font-medium text-gray-900">
                      {systemMetrics.system_uptime}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-medium text-gray-600">
                      Database Size:
                    </span>
                    <span className="text-sm font-medium text-gray-900">
                      {systemMetrics.database_size}
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-gray-500">Loading system status...</p>
              )}
            </div>

            {/* System Configuration */}
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                System Configuration
              </h2>
              {systemConfig ? (
                <div className="space-y-3">
                  <div className="flex justify-between">
                    <span className="text-sm font-medium text-gray-600">
                      Auto Backup:
                    </span>
                    <span
                      className={`text-sm font-medium ${
                        systemConfig.auto_backup_enabled
                          ? "text-green-600"
                          : "text-red-600"
                      }`}
                    >
                      {systemConfig.auto_backup_enabled
                        ? "Enabled"
                        : "Disabled"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-medium text-gray-600">
                      Backup Frequency:
                    </span>
                    <span className="text-sm font-medium text-gray-900">
                      {systemConfig.backup_frequency}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-medium text-gray-600">
                      Session Timeout:
                    </span>
                    <span className="text-sm font-medium text-gray-900">
                      {systemConfig.session_timeout} min
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-sm font-medium text-gray-600">
                      NFC Scan Timeout:
                    </span>
                    <span className="text-sm font-medium text-gray-900">
                      {systemConfig.nfc_scan_timeout} sec
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-gray-500">Loading configuration...</p>
              )}
              <button
                onClick={() => setShowConfigModal(true)}
                className="mt-4 w-full px-4 py-2 text-sm text-white bg-blue-600 rounded hover:bg-blue-700"
              >
                Edit Configuration
              </button>
            </div>

            {/* Quick Actions */}
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                Quick Actions
              </h2>
              <div className="space-y-3">
                <button
                  onClick={handleGenerateReport}
                  disabled={isLoading}
                  className="w-full px-4 py-2 text-sm text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50"
                >
                  {isLoading ? "Generating..." : "Generate System Report"}
                </button>
                <button
                  onClick={handleExportData}
                  disabled={isLoading}
                  className="w-full px-4 py-2 text-sm text-white bg-green-600 rounded hover:bg-green-700 disabled:opacity-50"
                >
                  {isLoading ? "Exporting..." : "Export All Data"}
                </button>
                <button
                  onClick={handleCreateBackup}
                  disabled={isLoading}
                  className="w-full px-4 py-2 text-sm text-white bg-purple-600 rounded hover:bg-purple-700 disabled:opacity-50"
                >
                  {isLoading ? "Creating..." : "Create Backup"}
                </button>
                <button
                  onClick={handleMaintenance}
                  disabled={isLoading}
                  className="w-full px-4 py-2 text-sm text-white bg-orange-600 rounded hover:bg-orange-700 disabled:opacity-50"
                >
                  {isLoading ? "Maintaining..." : "System Maintenance"}
                </button>
                <button
                  onClick={handleEmergencyShutdown}
                  disabled={isLoading}
                  className="w-full px-4 py-2 text-sm text-white bg-red-600 rounded hover:bg-red-700 disabled:opacity-50"
                >
                  {isLoading ? "Shutting down..." : "Emergency Shutdown"}
                </button>
              </div>
            </div>
          </div>

          {/* User Management */}
          <div className="mt-6 bg-white shadow rounded-lg p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-gray-900">
                User Management
              </h2>
              <button
                onClick={() => setShowAddStudentModal(true)}
                className="px-4 py-2 text-sm text-white bg-green-600 rounded hover:bg-green-700"
              >
                Add New Student
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Name
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Email
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Role
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Created
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Actions
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {users.map((user) => (
                    <tr key={user.id}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {user.name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {user.email}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {user.role}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                            user.is_active
                              ? "bg-green-100 text-green-800"
                              : "bg-red-100 text-red-800"
                          }`}
                        >
                          {user.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatDate(user.created_at)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                        <select
                          value={user.role}
                          onChange={(e) =>
                            updateUserRole(user.id, e.target.value)
                          }
                          className="mr-2 border border-gray-300 rounded px-2 py-1 text-sm"
                        >
                          <option value="student">Student</option>
                          <option value="teacher">Teacher</option>
                          <option value="it_staff">IT Staff</option>
                          <option value="admin">Admin</option>
                        </select>
                        <button
                          onClick={() => deleteUser(user.id)}
                          className="text-red-600 hover:text-red-900"
                        >
                          Delete
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Recent Audit Logs */}
          <div className="mt-6 bg-white shadow rounded-lg p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Recent Audit Logs
            </h2>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Timestamp
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      User
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Action
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Details
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      IP Address
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {auditLogs.map((log) => (
                    <tr key={log.id}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatTime(log.timestamp)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        User {log.user_id}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {log.action}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {log.details}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {log.ip_address || "N/A"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </main>

      {/* Configuration Modal */}
      {showConfigModal && systemConfig && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <h3 className="text-lg font-bold text-gray-900 mb-4">
              Edit System Configuration
            </h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Auto Backup
                </label>
                <input
                  type="checkbox"
                  checked={systemConfig.auto_backup_enabled}
                  onChange={(e) =>
                    setSystemConfig({
                      ...systemConfig,
                      auto_backup_enabled: e.target.checked,
                    })
                  }
                  className="h-4 w-4 text-blue-600"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Backup Frequency
                </label>
                <select
                  value={systemConfig.backup_frequency}
                  onChange={(e) =>
                    setSystemConfig({
                      ...systemConfig,
                      backup_frequency: e.target.value,
                    })
                  }
                  className="w-full border border-gray-300 rounded px-3 py-2"
                >
                  <option value="daily">Daily</option>
                  <option value="weekly">Weekly</option>
                  <option value="monthly">Monthly</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Session Timeout (minutes)
                </label>
                <input
                  type="number"
                  value={systemConfig.session_timeout}
                  onChange={(e) =>
                    setSystemConfig({
                      ...systemConfig,
                      session_timeout: parseInt(e.target.value),
                    })
                  }
                  className="w-full border border-gray-300 rounded px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  NFC Scan Timeout (seconds)
                </label>
                <input
                  type="number"
                  value={systemConfig.nfc_scan_timeout}
                  onChange={(e) =>
                    setSystemConfig({
                      ...systemConfig,
                      nfc_scan_timeout: parseInt(e.target.value),
                    })
                  }
                  className="w-full border border-gray-300 rounded px-3 py-2"
                />
              </div>
            </div>
            <div className="mt-6 flex justify-end space-x-3">
              <button
                onClick={() => setShowConfigModal(false)}
                className="px-4 py-2 text-sm text-gray-700 bg-gray-200 rounded hover:bg-gray-300"
              >
                Cancel
              </button>
              <button
                onClick={updateSystemConfig}
                className="px-4 py-2 text-sm text-white bg-blue-600 rounded hover:bg-blue-700"
              >
                Save Changes
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Add Student Modal */}
      <AddStudentModal
        isOpen={showAddStudentModal}
        onClose={() => {
          setShowAddStudentModal(false);
          setNewlyCreatedStudentId(null);
        }}
        onAddStudent={async (student) => {
          setIsAddingStudent(true);
          try {
            const token = localStorage.getItem("token");
            const headers = {
              Authorization: `Bearer ${token}`,
              "Content-Type": "application/json",
            };

            const response = await fetch(
              "http://localhost:8000/admin/students",
              {
                method: "POST",
                headers,
                body: JSON.stringify({
                  name: student.name,
                  class_name: student.class,
                }),
              }
            );

            if (response.ok) {
              const result = await response.json();
              setNewlyCreatedStudentId(result.student_id);
              await fetchDashboardData(); // Refresh data
            } else {
              setError("Failed to add student");
            }
          } catch {
            setError("Failed to add student");
          } finally {
            setIsAddingStudent(false);
          }
        }}
        onRegisterNfcTag={async (studentId) => {
          const token = localStorage.getItem("token");
          const headers = {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
          };

          const response = await fetch(
            "http://localhost:8000/it/register-tag",
            {
              method: "POST",
              headers,
              body: JSON.stringify({
                student_id: studentId,
                student_name: "New Student", // This will be updated by backend
              }),
            }
          );

          if (!response.ok) {
            throw new Error("Failed to register NFC tag");
          }
        }}
        isLoading={isAddingStudent}
        studentId={newlyCreatedStudentId}
      />
    </div>
  );
}
