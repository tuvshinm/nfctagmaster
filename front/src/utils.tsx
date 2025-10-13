import type { Student } from "./types";

export function downloadCSV(data: Student[]) {
  // Create CSV content in memory
  const csvContent = [
    ["ID", "UID", "NAME", "STATUS", "LAST_SCAN"], // Headers
    ...data.map((student) => [
      student.id,
      student.uid,
      student.name,
      student.status === true ? "IN" : "OUT",
      student.lastscan,
    ]),
  ]
    .map((row) => row.join(","))
    .join("\n");

  // Create Blob and download
  const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
  const link = document.createElement("a");

  if (link.download !== undefined) {
    const url = URL.createObjectURL(blob);
    link.setAttribute("href", url);
    link.setAttribute("download", "students.csv");
    link.style.visibility = "hidden";
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  }
}
