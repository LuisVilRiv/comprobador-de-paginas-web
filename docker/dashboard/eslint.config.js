import js from "@eslint/js";
import globals from "globals";

export default [
  js.configs.recommended,
  {
    files: ["frontend/**/*.js", "server.js"],
    ignores: ["frontend/**/*.test.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: {
        ...globals.browser,
        ...globals.node,
        React: "readonly",
        ReactDOM: "readonly",
        lucide: "readonly",
        driver: "readonly",
      },
    },
    rules: {
      "no-unused-vars": ["warn", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
      "no-undef": "error",
      "no-console": "off",
      "no-constant-condition": "warn",
      "no-debugger": "error",
      "no-duplicate-case": "error",
      "no-empty": ["warn", { allowEmptyCatch: true }],
      eqeqeq: ["warn", "smart"],
      "no-eval": "error",
      "no-implied-eval": "error",
      "prefer-const": "warn",
    },
  },
  {
    files: ["frontend/**/*.test.js"],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: "module",
      globals: {
        ...globals.browser,
        ...globals.node,
        ...globals.jest,
      },
      parserOptions: {
        ecmaFeatures: { jsx: true },
      },
    },
    rules: {
      "no-unused-vars": ["warn", { argsIgnorePattern: "^_", varsIgnorePattern: "^_" }],
      "no-undef": "error",
    },
  },
];
