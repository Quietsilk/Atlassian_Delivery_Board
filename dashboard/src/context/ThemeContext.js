import { createContext, useContext } from "react";
import { getTokens } from "../tokens";

export const ThemeContext = createContext(getTokens("dark"));
export const useT = () => useContext(ThemeContext);
