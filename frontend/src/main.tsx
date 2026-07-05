// Amplify の configure は副作用 import で行う。他の import より先に評価される必要があるため最先頭に置く。
import "./auth/amplify-config";
// Amplify Hub event listener も Amplify.configure() の後に登録する必要があるので
// amplify-config の直後に副作用 import する。
import "./auth/auth-hub-listener";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import App from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>
);
