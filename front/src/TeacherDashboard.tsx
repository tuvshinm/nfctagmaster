import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { AddStudentModal } from "./components/AddStudentModal";

interface Student {
  id: number;
  name: string;
  tid: string;
  in_school: boolean;
  last_scan: number;
  last_scan_time?: string;
}

interface DutyTeacher {
  teacher_name: string;
  teacher_id: number;
}

interface CheckInLog {
  id: number;
  user_id: number;
  action: string;
  timestamp: string;
  details: string;
  ip_address?: string;
}

export function TeacherDashboard() {
  const navigate = useNavigate();
  const [currentDuty, setCurrentDuty] = useState<DutyTeacher | null>(null);
  const [students, setStudents] = useState<Student[]>([]);
  const [checkInLogs, setCheckInLogs] = useState<CheckInLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const [showAssignDuty, setShowAssignDuty] = useState(false);
  const [selectedTeacherId, setSelectedTeacherId] = useState<number>(1);
  const [showAddStudentModal, setShowAddStudentModal] = useState(false);
  const [newlyCreatedStudentId, setNewlyCreatedStudentId] = useState<
    number | null
  >(null);
  const [isAddingStudent, setIsAddingStudent] = useState(false);

  // Check authentication
  useEffect(() => {
    const token = localStorage.getItem("token");
    const userRole = localStorage.getItem("userRole");

    if (!token || userRole !== "teacher") {
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

      // Fetch current duty
      const dutyResponse = await fetch(
        "http://localhost:8000/teacher/current-duty",
        { headers }
      );
      if (dutyResponse.ok) {
        const dutyData = await dutyResponse.json();
        setCurrentDuty(dutyData);
      }

      // Fetch students
      const studentsResponse = await fetch(
        "http://localhost:8000/teacher/students",
        { headers }
      );
      if (studentsResponse.ok) {
        const studentsData = await studentsResponse.json();
        setStudents(studentsData.students);
      }

      // Fetch check-in logs
      const logsResponse = await fetch(
        "http://localhost:8000/teacher/check-in-logs",
        { headers }
      );
      if (logsResponse.ok) {
        const logsData = await logsResponse.json();
        setCheckInLogs(logsData.logs);
      }
    } catch {
      setError("Failed to load dashboard data");
    } finally {
      setIsLoading(false);
    }
  };

  const assignDuty = async () => {
    try {
      const token = localStorage.getItem("token");
      const headers = {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      };

      const response = await fetch(
        `http://localhost:8000/teacher/assign-duty/${selectedTeacherId}`,
        {
          method: "POST",
          headers,
        }
      );

      if (response.ok) {
        await fetchDashboardData(); // Refresh data
        setShowAssignDuty(false);
      } else {
        setError("Failed to assign duty");
      }
    } catch {
      setError("Failed to assign duty");
    }
  };

  const formatTime = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  // Add student handler
  const handleAddStudent = async (student: { name: string; class: string }) => {
    setIsAddingStudent(true);
    try {
      const token = localStorage.getItem("token");
      const headers = {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      };

      const response = await fetch("http://localhost:8000/teacher/students", {
        method: "POST",
        headers,
        body: JSON.stringify({
          name: student.name,
          class_name: student.class,
        }),
      });

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
  };

  // Handle NFC tag registration
  const handleRegisterNfcTag = async (studentId: number) => {
    const token = localStorage.getItem("token");
    const headers = {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    };

    const response = await fetch("http://localhost:8000/teacher/register-tag", {
      method: "POST",
      headers,
      body: JSON.stringify({
        student_id: studentId,
        student_name: "New Student", // This will be updated by backend
      }),
    });

    if (!response.ok) {
      throw new Error("Failed to register NFC tag");
    }
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
                Teacher Dashboard
              </h1>
              <p className="mt-1 text-sm text-gray-600">
                NFC Attendance Management System
              </p>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">Welcome, Teacher</span>
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

        <div className="px-4 py-6 sm:px-0">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Current Duty */}
            <div className="bg-white shadow rounded-lg p-6">
              <div className="flex justify-between items-center mb-4">
                <h2 className="text-xl font-semibold text-gray-900">
                  Current Duty
                </h2>
                <button
                  onClick={() => setShowAssignDuty(true)}
                  className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700"
                >
                  Assign Duty
                </button>
              </div>
              {currentDuty ? (
                <div className="space-y-2">
                  <p>
                    <span className="font-medium">Teacher:</span>{" "}
                    {currentDuty.teacher_name}
                  </p>
                  <p>
                    <span className="font-medium">ID:</span>{" "}
                    {currentDuty.teacher_id}
                  </p>
                </div>
              ) : (
                <p className="text-gray-500">No teacher currently on duty</p>
              )}
            </div>

            {/* Quick Stats */}
            <div className="bg-white shadow rounded-lg p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">
                Quick Stats
              </h2>
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center">
                  <div className="text-2xl font-bold text-blue-600">
                    {students.length}
                  </div>
                  <div className="text-sm text-gray-600">Total Students</div>
                </div>
                <div className="text-center">
                  <div className="text-2xl font-bold text-green-600">
                    {students.filter((s) => s.in_school).length}
                  </div>
                  <div className="text-sm text-gray-600">Present</div>
                </div>
              </div>
            </div>
          </div>

          {/* Students Check-in Status */}
          <div className="mt-6 bg-white shadow rounded-lg p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-semibold text-gray-900">
                Student Check-in Status
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
                      Student ID
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Status
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Last Scan
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {students.map((student) => (
                    <tr key={student.id}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                        {student.name}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {student.id}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${
                            student.in_school
                              ? "bg-green-100 text-green-800"
                              : "bg-red-100 text-red-800"
                          }`}
                        >
                          {student.in_school ? "In School" : "Not in School"}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {student.last_scan_time ||
                          new Date(student.last_scan * 1000).toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>

          {/* Recent Check-in Logs */}
          <div className="mt-6 bg-white shadow rounded-lg p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">
              Recent Check-in Logs
            </h2>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Time
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Action
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Details
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {checkInLogs.slice(0, 10).map((log) => (
                    <tr key={log.id}>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        {formatTime(log.timestamp)}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                        {log.action.replace("_", " ").toUpperCase()}
                      </td>
                      <td className="px-6 py-4 text-sm text-gray-500">
                        {log.details}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </main>

      {/* Assign Duty Modal */}
      {showAssignDuty && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full">
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
            <h3 className="text-lg font-bold text-gray-900 mb-4">
              Assign Duty
            </h3>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Teacher
              </label>
              <select
                value={selectedTeacherId}
                onChange={(e) => setSelectedTeacherId(Number(e.target.value))}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {/* In a real app, this would fetch teachers from the API */}
                <option value={1}>Teacher 1</option>
                <option value={2}>Teacher 2</option>
                <option value={3}>Teacher 3</option>
              </select>
            </div>
            <div className="flex justify-end space-x-3">
              <button
                onClick={() => setShowAssignDuty(false)}
                className="px-4 py-2 text-sm text-gray-700 bg-gray-200 rounded hover:bg-gray-300"
              >
                Cancel
              </button>
              <button
                onClick={assignDuty}
                className="px-4 py-2 text-sm text-white bg-blue-600 rounded hover:bg-blue-700"
              >
                Assign Duty
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
        onAddStudent={handleAddStudent}
        onRegisterNfcTag={handleRegisterNfcTag}
        isLoading={isAddingStudent}
        studentId={newlyCreatedStudentId}
      />
    </div>
  );
}
