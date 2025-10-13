import { StudentTable } from "./StudentTable";
import { mock_data } from "../MOCK_DATA";
function App() {
  return (
    <>
      <div className="flex flex-row justify-center items-center h-screen">
        <StudentTable data={mock_data} />
      </div>
    </>
  );
}

export default App;
