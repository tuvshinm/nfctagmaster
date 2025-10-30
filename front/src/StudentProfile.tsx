import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";

interface Student {
  id: number;
  name: string;
  uid: string;
  status: boolean;
  lastscan: number;
}

interface CheckInLog {
  id: number;
  action: string;
  timestamp: string;
  details: string;
  user_id: number;
}

export function StudentProfile() {
  const [student, setStudent] = useState<Student | null>(null);
  const [logs, setLogs] = useState<CheckInLog[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    // Get student ID from URL or localStorage
    const studentId =
      new URLSearchParams(window.location.search).get("id") ||
      localStorage.getItem("selectedStudentId");

    if (!studentId) {
      setError("Student ID not provided");
      setIsLoading(false);
      return;
    }

    fetchStudentData(studentId);
  }, []);

  const fetchStudentData = async (studentId: string) => {
    try {
      const token = localStorage.getItem("token");
      if (!token) {
        navigate("/login");
        return;
      }

      const [studentResponse, logsResponse] = await Promise.all([
        fetch(`http://localhost:8000/teacher/students/${studentId}`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }),
        fetch(`http://localhost:8000/teacher/check-in-logs`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }),
      ]);

      if (studentResponse.ok) {
        const studentData = await studentResponse.json();
        setStudent(studentData);
      }

      if (logsResponse.ok) {
        const logsData = await logsResponse.json();
        // Filter logs for this specific student
        const studentLogs = logsData.logs.filter(
          (log: CheckInLog) =>
            log.details.includes(studentId) ||
            log.user_id === parseInt(studentId)
        );
        setLogs(studentLogs);
      }
    } catch (err) {
      setError("Failed to fetch student data");
    } finally {
      setIsLoading(false);
    }
  };

  const getStatusColor = (status: boolean) => {
    return status ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800";
  };

  const getStatusText = (status: boolean) => {
    return status ? "IN SCHOOL" : "OUT OF SCHOOL";
  };

  const formatDate = (timestamp: string) => {
    return new Date(timestamp).toLocaleString();
  };

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-red-600 text-lg">{error}</div>
      </div>
    );
  }

  if (!student) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Student not found</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Student Header */}
        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-2xl font-bold text-gray-900">{student.name}</h1>
            <span
              className={`inline-flex px-3 py-1 text-sm font-semibold rounded-full ${getStatusColor(
                student.status
              )}`}
            >
              {getStatusText(student.status)}
            </span>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <h3 className="text-sm font-medium text-gray-500">Student ID</h3>
              <p className="text-lg text-gray-900">{student.id}</p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-500">NFC Tag ID</h3>
              <p className="text-lg font-mono text-gray-900">{student.uid}</p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-500">Last Scan</h3>
              <p className="text-lg text-gray-900">
                {student.lastscan
                  ? new Date(student.lastscan * 1000).toLocaleString()
                  : "Never"}
              </p>
            </div>
            <div>
              <h3 className="text-sm font-medium text-gray-500">
                Current Status
              </h3>
              <p className="text-lg text-gray-900">
                {student.status ? "Present in school" : "Absent from school"}
              </p>
            </div>
          </div>
        </div>

        {/* Activity History */}
        <div className="bg-white shadow rounded-lg">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-xl font-semibold text-gray-900">
              Activity History
            </h2>
            <p className="mt-1 text-sm text-gray-600">
              Recent check-in/out activities
            </p>
          </div>

          <div className="divide-y divide-gray-200">
            {logs.length > 0 ? (
              logs.map((log) => (
                <div key={log.id} className="px-6 py-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-3">
                      <div
                        className={`w-3 h-3 rounded-full ${
                          log.action.includes("check_in")
                            ? "bg-green-500"
                            : "bg-red-500"
                        }`}
                      ></div>
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {log.action.includes("check_in")
                            ? "Checked In"
                            : "Checked Out"}
                        </p>
                        <p className="text-sm text-gray-500">{log.details}</p>
                      </div>
                    </div>
                    <div className="text-sm text-gray-500">
                      {formatDate(log.timestamp)}
                    </div>
                  </div>
                </div>
              ))
            ) : (
              <div className="px-6 py-8 text-center">
                <p className="text-gray-500">No activity history found</p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
