import { useState } from "react";
import ReactDOM from "react-dom/client";
import Loader from "./Loader";
import Demo from "./Demo";
import "./theme.css";

function Root() {
  const [entered, setEntered] = useState(false);
  return (
    <>
      {!entered && <Loader onDone={() => setEntered(true)} />}
      <Demo />
    </>
  );
}

ReactDOM.createRoot(document.getElementById("demo-root")!).render(<Root />);
