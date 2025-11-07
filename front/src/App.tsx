import {
  BrowserRouter as Router,
  Routes,
  Route,
  Navigate,
} from "react-router-dom";
import { StudentTable } from "./StudentTable";
import { StudentProfile } from "./StudentProfile";
import { LoginPage } from "./Login";
import { RegisterPage } from "./RegisterPage";
import { TeacherDashboard } from "./TeacherDashboard";
import { ITStaffDashboard } from "./ITStaffDashboard";
import { AdminDashboard } from "./AdminDashboard";

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/students" element={<StudentTable />} />
        <Route path="/student/:id" element={<StudentProfile />} />
        <Route path="/teacher" element={<TeacherDashboard />} />
        <Route path="/it-staff" element={<ITStaffDashboard />} />
        <Route path="/admin" element={<AdminDashboard />} />
      </Routes>
    </Router>
  );
}

export default App;
