import React from "react";
import { render, act } from "@testing-library/react";
import { I18nProvider, useI18n } from "./i18n.js";


// Simple dummy consumer component for testing Context values
function TestConsumer({ translationKey }) {
  const { lang, toggleLang, t } = useI18n();
  return (
    <div>
      <span data-testid="lang">{lang}</span>
      <span data-testid="translation">{t(translationKey)}</span>
      <button data-testid="toggle-btn" onClick={toggleLang}>Toggle</button>
    </div>
  );
}


describe("Internationalization System (10 Test Cases)", () => {
  
  beforeEach(() => {
    localStorage.clear();
    document.documentElement.lang = "es";
  });

  test("Initializes default language to 'es' when localstorage is empty", () => {
    const { getByTestId } = render(
      <I18nProvider>
        <TestConsumer translationKey="app.title" />
      </I18nProvider>
    );
    expect(getByTestId("lang").textContent).toBe("es");
  });

  test("Translates spanish keys successfully on default mode", () => {
    const { getByTestId } = render(
      <I18nProvider>
        <TestConsumer translationKey="app.title" />
      </I18nProvider>
    );
    expect(getByTestId("translation").textContent).toBe("Web Auditor Dashboard");
  });

  test("Falls back to raw key if translation key is missing in dictionary", () => {
    const { getByTestId } = render(
      <I18nProvider>
        <TestConsumer translationKey="non.existent.key" />
      </I18nProvider>
    );
    expect(getByTestId("translation").textContent).toBe("non.existent.key");
  });

  test("Loads preferred language from localStorage on initial render", () => {
    localStorage.setItem("app_lang", "en");
    const { getByTestId } = render(
      <I18nProvider>
        <TestConsumer translationKey="app.title" />
      </I18nProvider>
    );
    expect(getByTestId("lang").textContent).toBe("en");
    expect(getByTestId("translation").textContent).toBe("Web Auditor Dashboard");
  });

  test("Toggles language successfully between 'es' and 'en'", () => {
    const { getByTestId } = render(
      <I18nProvider>
        <TestConsumer translationKey="app.excellent_score" />
      </I18nProvider>
    );
    
    expect(getByTestId("lang").textContent).toBe("es");
    expect(getByTestId("translation").textContent).toBe("PUNTUACIÓN EXCELENTE");

    act(() => {
      getByTestId("toggle-btn").click();
    });

    expect(getByTestId("lang").textContent).toBe("en");
    expect(getByTestId("translation").textContent).toBe("EXCELLENT SCORE");
  });

  test("Updates localStorage value after toggling language", () => {
    const { getByTestId } = render(
      <I18nProvider>
        <TestConsumer translationKey="app.title" />
      </I18nProvider>
    );

    act(() => {
      getByTestId("toggle-btn").click();
    });

    expect(localStorage.getItem("app_lang")).toBe("en");
  });

  test("Updates document.documentElement.lang attribute after toggling", () => {
    const { getByTestId } = render(
      <I18nProvider>
        <TestConsumer translationKey="app.title" />
      </I18nProvider>
    );

    act(() => {
      getByTestId("toggle-btn").click();
    });

    expect(document.documentElement.lang).toBe("en");
  });

  test("Translates nested keys correctly in both languages", () => {
    const { getByTestId, rerender } = render(
      <I18nProvider>
        <TestConsumer translationKey="modals.close" />
      </I18nProvider>
    );
    expect(getByTestId("translation").textContent).toBe("Cerrar");

    act(() => {
      getByTestId("toggle-btn").click();
    });
    expect(getByTestId("translation").textContent).toBe("Close");
  });

  test("Handles partial missing subkeys gracefully and returns last available branch or raw key", () => {
    const { getByTestId } = render(
      <I18nProvider>
        <TestConsumer translationKey="app.title.missing.subkey" />
      </I18nProvider>
    );
    expect(getByTestId("translation").textContent).toBe("app.title.missing.subkey");
  });

  test("Verify toggle Lang loops correctly back to 'es' when clicked twice", () => {
    const { getByTestId } = render(
      <I18nProvider>
        <TestConsumer translationKey="app.title" />
      </I18nProvider>
    );
    
    act(() => {
      getByTestId("toggle-btn").click(); // to en
      getByTestId("toggle-btn").click(); // back to es
    });

    expect(getByTestId("lang").textContent).toBe("es");
  });

});
