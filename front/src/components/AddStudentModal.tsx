import { useState, type FormEvent } from "react";

interface Student {
  name: string;
  class: string;
}

interface AddStudentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAddStudent: (student: Student) => void;
  onRegisterNfcTag?: (studentId: number, studentName: string) => Promise<void>;
  isLoading?: boolean;
  studentId?: number | null;
}

export function AddStudentModal({
  isOpen,
  onClose,
  onAddStudent,
  onRegisterNfcTag,
  isLoading = false,
  studentId,
}: AddStudentModalProps) {
  const [name, setName] = useState("");
  const [classValue, setClassValue] = useState("");
  const [error, setError] = useState("");
  const [isRegisteringNfc, setIsRegisteringNfc] = useState(false);
  const [showNfcRegistration, setShowNfcRegistration] = useState(false);

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !classValue.trim()) {
      setError("Please fill in all fields");
      return;
    }
    if (name.trim().length < 2) {
      setError("Name must be at least 2 characters long");
      return;
    }
    onAddStudent({ name: name.trim(), class: classValue.trim() });
    setError("");
    setShowNfcRegistration(true); // Show NFC registration option after successful student creation
  };

  const handleNfcRegistration = async () => {
    if (!studentId || !onRegisterNfcTag) return;

    setIsRegisteringNfc(true);
    try {
      await onRegisterNfcTag(studentId, name);
      setShowNfcRegistration(false);
      onClose();
    } catch (error) {
      setError("Failed to register NFC tag. Please try again.");
    } finally {
      setIsRegisteringNfc(false);
    }
  };

  const handleCancel = () => {
    setName("");
    setClassValue("");
    setError("");
    setShowNfcRegistration(false);
    onClose();
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
      <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white">
        <h3 className="text-lg font-bold text-gray-900 mb-4">
          {studentId ? "Register NFC Tag" : "Add New Student"}
        </h3>

        {!showNfcRegistration ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Student Name *
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter student name"
                required
                disabled={isLoading}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Class *
              </label>
              <input
                type="text"
                value={classValue}
                onChange={(e) => setClassValue(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="Enter class (e.g., Grade 10A)"
                required
                disabled={isLoading}
              />
            </div>

            {error && <div className="text-red-600 text-sm">{error}</div>}

            <div className="mt-6 flex justify-end space-x-3">
              <button
                type="button"
                onClick={handleCancel}
                disabled={isLoading}
                className="px-4 py-2 text-sm text-gray-700 bg-gray-200 rounded hover:bg-gray-300 disabled:opacity-50"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={isLoading || !name.trim() || !classValue.trim()}
                className="px-4 py-2 text-sm text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50"
              >
                {isLoading ? "Adding..." : "Add Student"}
              </button>
            </div>
          </form>
        ) : (
          <div className="space-y-4">
            <div className="text-center">
              <div className="text-green-600 text-sm mb-2">
                Student added successfully!
              </div>
              <p className="text-gray-600 text-sm">
                Would you like to register an NFC tag for this student now?
              </p>
            </div>
            <div className="bg-blue-50 border border-blue-200 rounded p-3">
              <p className="text-blue-800 text-sm">
                <strong>Instructions:</strong> Click "Register NFC Tag" and then
                tap an NFC tag on the reader when prompted.
              </p>
            </div>
            <div className="flex justify-end space-x-3">
              <button
                type="button"
                onClick={() => {
                  setShowNfcRegistration(false);
                  onClose();
                }}
                className="px-4 py-2 text-sm text-gray-700 bg-gray-200 rounded hover:bg-gray-300"
              >
                Skip for Now
              </button>
              <button
                type="button"
                onClick={handleNfcRegistration}
                className="px-4 py-2 text-sm text-white bg-green-600 rounded hover:bg-green-700 disabled:opacity-50"
                disabled={isRegisteringNfc}
              >
                {isRegisteringNfc ? "Registering..." : "Register NFC Tag"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
