import { useState, useEffect, useCallback, useRef } from "react";
import { toast } from "../components/Toast";

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

  // Refs to track previous states for change detection
  const previousStudentsRef = useRef<Student[]>([]);
  const previousLogsRef = useRef<CheckInLog[]>([]);

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
        const newStudents = studentsData.students;

        // Detect student status changes and show toast notifications
        const previousStudents = previousStudentsRef.current;
        previousStudentsRef.current = newStudents;

        newStudents.forEach((student: Student) => {
          const previousStudent = previousStudents.find(
            (s) => s.id === student.id
          );
          if (
            previousStudent &&
            previousStudent.in_school !== student.in_school
          ) {
            const action = student.in_school ? "checked in" : "checked out";
            toast.success(`${student.name} has ${action}!`);
          }
        });

        setStudents(newStudents);
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
        const newLogs = logsData.logs;

        // Detect new logs and show toast notifications
        const previousLogs = previousLogsRef.current;
        previousLogsRef.current = newLogs;

        const newLogEntries = newLogs.filter(
          (log: CheckInLog) =>
            !previousLogs.some((prevLog) => prevLog.id === log.id)
        );

        newLogEntries.forEach((log: CheckInLog) => {
          if (log.action.includes("check_in")) {
            toast.info(`Check-in recorded: ${log.details}`);
          } else if (log.action.includes("check_out")) {
            toast.info(`Check-out recorded: ${log.details}`);
          }
        });

        setCheckInLogs(newLogs);
      }

      setLastUpdate(new Date());
    } catch (error) {
      console.error("Error fetching real-time updates:", error);
      toast.error("Failed to fetch real-time updates");
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Set up periodic polling for real-time updates
  useEffect(() => {
    fetchData(); // Initial fetch

    const interval = setInterval(() => {
      fetchData();
    }, 5000); // Poll every 5 seconds

    return () => clearInterval(interval);
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
