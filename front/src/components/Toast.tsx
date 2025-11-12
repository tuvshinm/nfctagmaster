import { useEffect, useState } from "react";

interface ToastProps {
  message: string;
  type: "success" | "error" | "info" | "warning";
  duration?: number;
  onClose: () => void;
}

export function Toast({ message, type, duration = 3000, onClose }: ToastProps) {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    const timer = setTimeout(() => {
      setIsVisible(false);
      setTimeout(onClose, 300); // Wait for animation to finish
    }, duration);

    return () => clearTimeout(timer);
  }, [duration, onClose]);

  const bgColor = {
    success: "bg-green-500",
    error: "bg-red-500",
    info: "bg-blue-500",
    warning: "bg-yellow-500",
  }[type];

  return (
    <div
      className={`fixed top-4 right-4 z-50 transform transition-all duration-300 ${
        isVisible ? "translate-x-0 opacity-100" : "translate-x-full opacity-0"
      }`}
    >
      <div
        className={`${bgColor} text-white px-6 py-3 rounded-lg shadow-lg flex items-center space-x-2 min-w-[300px]`}
      >
        <span>{message}</span>
        <button
          onClick={() => {
            setIsVisible(false);
            setTimeout(onClose, 300);
          }}
          className="ml-4 text-white hover:text-gray-200"
        >
          ✕
        </button>
      </div>
    </div>
  );
}

interface ToastMessage {
  id: string;
  message: string;
  type: "success" | "error" | "info" | "warning";
}

export function ToastContainer() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const addToast = (
    message: string,
    type: "success" | "error" | "info" | "warning" = "info"
  ) => {
    const id = Math.random().toString(36).substr(2, 9);
    setToasts((prev) => [...prev, { id, message, type }]);
  };

  const removeToast = (id: string) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  };

  // Register callbacks with global toast functions
  useEffect(() => {
    registerToastCallbacks({
      success: addToast,
      error: addToast,
      info: addToast,
      warning: addToast,
    });
  }, []);

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2">
      {toasts.map((toast) => (
        <Toast
          key={toast.id}
          message={toast.message}
          type={toast.type}
          onClose={() => removeToast(toast.id)}
        />
      ))}
    </div>
  );
}

// Global toast functions
let toastCallbacks: {
  success: (message: string) => void;
  error: (message: string) => void;
  info: (message: string) => void;
  warning: (message: string) => void;
} | null = null;

export const toast = {
  success: (message: string) => {
    if (toastCallbacks) toastCallbacks.success(message);
    console.log("Toast success:", message);
  },
  error: (message: string) => {
    if (toastCallbacks) toastCallbacks.error(message);
    console.log("Toast error:", message);
  },
  info: (message: string) => {
    if (toastCallbacks) toastCallbacks.info(message);
    console.log("Toast info:", message);
  },
  warning: (message: string) => {
    if (toastCallbacks) toastCallbacks.warning(message);
    console.log("Toast warning:", message);
  },
};

// ToastContainer will register its callbacks here
export function registerToastCallbacks(callbacks: typeof toastCallbacks) {
  toastCallbacks = callbacks;
}
