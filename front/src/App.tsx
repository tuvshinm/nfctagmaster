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

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Navigate to="/students" replace />} />
        <Route path="/students" element={<StudentTable />} />
        <Route path="/student/:id" element={<StudentProfile />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
      </Routes>
    </Router>
  );
}

export default App;
