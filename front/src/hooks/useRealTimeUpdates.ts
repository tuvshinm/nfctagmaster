import { useState, useEffect, useCallback } from "react";

interface Student {
  id: number;
  name: string;
  tid: string;
  in_school: boolean;
  last_scan: number;
  last_scan_time?: string;
}

interface CheckInLog {
  id: number;
  user_id: number;
  action: string;
  timestamp: string;
  details: string;
  ip_address?: string;
}

export function useRealTimeUpdates() {
  const [students, setStudents] = useState<Student[]>([]);
  const [checkInLogs, setCheckInLogs] = useState<CheckInLog[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [lastUpdate, setLastUpdate] = useState<Date | null>(null);

  // Fetch current data
  const fetchData = useCallback(async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem("token");
      const headers = {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      };

      // Fetch students
      const studentsResponse = await fetch("http://localhost:8000/students", {
        headers,
      });
      if (studentsResponse.ok) {
        const studentsData = await studentsResponse.json();
        setStudents(studentsData.students);
      }

      // Fetch check-in logs
      const logsResponse = await fetch(
        "http://localhost:8000/teacher/check-in-logs",
        {
          headers,
        }
      );
      if (logsResponse.ok) {
        const logsData = await logsResponse.json();
        setCheckInLogs(logsData.logs);
      }

      setLastUpdate(new Date());
    } catch (error) {
      console.error("Error fetching data:", error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Initial fetch only
  useEffect(() => {
    fetchData();
  }, [fetchData]);

  // Manual refresh function
  const refresh = useCallback(() => {
    fetchData();
  }, [fetchData]);

  return {
    students,
    checkInLogs,
    isLoading,
    lastUpdate,
    refresh,
  };
}
