import { useState, useEffect } from "react";

interface Student {
  id: number;
  name: string;
  tid?: string;
  class_name?: string;
}

interface NfcRegistrationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onRegisterNfcTag: (studentId: number, studentName: string) => Promise<void>;
  isLoading?: boolean;
  students?: Student[];
}

export function NfcRegistrationModal({
  isOpen,
  onClose,
  onRegisterNfcTag,
  isLoading = false,
  students = [],
}: NfcRegistrationModalProps) {
  const [selectedStudent, setSelectedStudent] = useState<Student | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [filteredStudents, setFilteredStudents] = useState<Student[]>([]);
  const [isRegistering, setIsRegistering] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (searchTerm.trim() === "") {
      setFilteredStudents(students);
    } else {
      const filtered = students.filter((student) =>
        student.name.toLowerCase().includes(searchTerm.toLowerCase())
      );
      setFilteredStudents(filtered);
    }
  }, [searchTerm, students]);

  const handleRegister = async () => {
    if (!selectedStudent) {
      setError("Please select a student");
      return;
    }

    setIsRegistering(true);
    try {
      await onRegisterNfcTag(selectedStudent.id, selectedStudent.name);
      onClose();
    } catch {
      setError("Failed to register NFC tag. Please try again.");
    } finally {
      setIsRegistering(false);
    }
  };

  const handleCancel = () => {
    setSelectedStudent(null);
    setSearchTerm("");
    setError("");
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
        <h3 className="text-lg font-bold text-gray-900 mb-4">
          Register NFC Tag
        </h3>

        <div className="space-y-4">
          {/* Student Search */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Select Student *
            </label>
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Search for a student by name..."
              disabled={isLoading}
            />
          </div>

          {/* Student List */}
          {filteredStudents.length > 0 && (
            <div className="border border-gray-200 rounded-md max-h-40 overflow-y-auto">
              {filteredStudents.map((student) => (
                <div
                  key={student.id}
                  className={`p-3 cursor-pointer hover:bg-gray-50 ${
                    selectedStudent?.id === student.id
                      ? "bg-blue-50 border-blue-200"
                      : "border-b border-gray-100"
                  }`}
                  onClick={() => setSelectedStudent(student)}
                >
                  <div className="font-medium text-sm text-gray-900">
                    {student.name}
                  </div>
                  {student.class_name && (
                    <div className="text-xs text-gray-500">
                      {student.class_name}
                    </div>
                  )}
                  <div className="text-xs text-gray-400">ID: {student.id}</div>
                </div>
              ))}
            </div>
          )}

          {filteredStudents.length === 0 && searchTerm.trim() !== "" && (
            <div className="text-sm text-gray-500 text-center py-2">
              No students found matching "{searchTerm}"
            </div>
          )}

          {/* Selected Student Info */}
          {selectedStudent && (
            <div className="bg-blue-50 border border-blue-200 rounded p-3">
              <div className="text-sm font-medium text-blue-800 mb-1">
                Selected Student:
              </div>
              <div className="text-sm text-blue-700">
                <div>Name: {selectedStudent.name}</div>
                {selectedStudent.class_name && (
                  <div>Class: {selectedStudent.class_name}</div>
                )}
                <div>ID: {selectedStudent.id}</div>
              </div>
            </div>
          )}

          {/* Instructions */}
          <div className="bg-yellow-50 border border-yellow-200 rounded p-3">
            <p className="text-yellow-800 text-sm">
              <strong>Instructions:</strong> Select a student above, then click
              "Register NFC Tag" and tap an NFC tag on the reader when prompted.
            </p>
          </div>

          {error && (
            <div className="text-red-600 text-sm bg-red-50 p-2 rounded">
              {error}
            </div>
          )}

          {/* Action Buttons */}
          <div className="flex justify-end space-x-3">
            <button
              type="button"
              onClick={handleCancel}
              disabled={isLoading}
              className="px-4 py-2 text-sm text-gray-700 bg-gray-200 rounded hover:bg-gray-300 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleRegister}
              disabled={isLoading || isRegistering || !selectedStudent}
              className="px-4 py-2 text-sm text-white bg-green-600 rounded hover:bg-green-700 disabled:opacity-50"
            >
              {isRegistering ? "Registering..." : "Register NFC Tag"}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
