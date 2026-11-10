
import { useEffect, useRef, useState } from "react";
import {
  emptyDraft,
  type SettingsDraft,
  type FieldErrors,
} from "../../types/settings";
import {
  getAccountSettings,
  saveSettingsStep,
  submitAccountSettings,
} from "../../services/settingsApi";
import StepIndicator from "./StepIndicator";
import SettingsFields from "./SettingsFields";

interface Props {
  accountId: number;
  accountName: string;
  onClose: () => void;
}

const titles = [
  "Account details",
  "Subscription settings",
  "Usage limits",
  "Integrations",
];

function normalizeDraft(raw: Record<string, unknown>): SettingsDraft {
  const result = structuredClone(emptyDraft);

  for (const step of [1, 2, 3, 4] as const) {
    const candidate = raw[String(step)] as
      | { data?: Record<string, unknown> }
      | Record<string, unknown>
      | undefined;

    if (!candidate) continue;

    const data =
      "data" in candidate && candidate.data
        ? candidate.data
        : candidate;

    Object.assign(result[step], data);
  }

  return result;
}

function stepData(draft: SettingsDraft, step: number) {
  const data = { ...draft[step as keyof SettingsDraft] };

  // Convert numeric inputs to numbers, while preserving optional empties.
  if (step === 3) {
    const limits = data as SettingsDraft[3];
    return {
      minutes_cap: limits.minutes_cap === "" ? null : Number(limits.minutes_cap),
      sms_cap: limits.sms_cap === "" ? null : Number(limits.sms_cap),
    };
  }

  return data;
}

export default function SettingsWizard({
  accountId,
  accountName,
  onClose,
}: Props) {
  const [draft, setDraft] = useState<SettingsDraft>(
    () => structuredClone(emptyDraft)
  );
  const [step, setStep] = useState(1);
  const [completed, setCompleted] = useState<number[]>([]);
  const [errors, setErrors] = useState<FieldErrors>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [failure, setFailure] = useState("");
  const [submitted, setSubmitted] = useState(false);
  const headingRef = useRef<HTMLHeadingElement>(null);
  const saveTimer = useRef<number | undefined>(undefined);
  const latestDraft = useRef(draft);
  const savingRef = useRef(false);

  useEffect(() => {
    latestDraft.current = draft;
  }, [draft]);

  useEffect(() => {
    let alive = true;

    getAccountSettings(accountId)
      .then((raw) => {
        if (!alive) return;

        const restored = normalizeDraft(raw);
        setDraft(restored);
        latestDraft.current = restored;

        const saved = raw.saved_steps;

        if (Array.isArray(saved)) {
          setCompleted(saved.map(Number));
        } else {
          setCompleted(
            [1, 2, 3, 4].filter((number) => {
              const item = raw[String(number)];
              return item !== undefined && item !== null;
            })
          );
        }
      })
      .catch(() => {
        if (alive) setFailure("Could not restore saved settings. You can still edit the form.");
      })
      .finally(() => {
        if (alive) setLoading(false);
      });

    return () => {
      alive = false;
      window.clearTimeout(saveTimer.current);
    };
  }, [accountId]);

  useEffect(() => {
    headingRef.current?.focus();
  }, [step]);

  function changeField(field: string, value: string) {
    setDraft((current) => {
      const next = structuredClone(current);

      (next[step as keyof SettingsDraft] as unknown as Record<string, unknown>)[field] =
        step === 3 && value !== "" ? Number(value) : value;

      latestDraft.current = next;
      return next;
    });

    setErrors((current) => ({ ...current, [field]: "" }));
    setFailure("");
    setMessage("Draft changed. Autosaving...");

    window.clearTimeout(saveTimer.current);

    // Debounced autosave. Required fields are validated by the server.
    saveTimer.current = window.setTimeout(() => {
      void saveStep(step);
    }, 900);
  }

  async function saveStep(targetStep: number): Promise<boolean> {
    if (savingRef.current) return false;

    savingRef.current = true;
    setSaving(true);
    setErrors({});
    setFailure("");
    setMessage("Saving...");

    try {
      await saveSettingsStep(
        accountId,
        targetStep,
        stepData(latestDraft.current, targetStep)
      );

      setCompleted((previous) =>
        previous.includes(targetStep) ? previous : [...previous, targetStep]
      );

      setMessage(`Step ${targetStep} saved successfully.`);
      return true;
    } catch (error) {
      const body = (error as { body?: { detail?: unknown } }).body;
      const detail = body?.detail as
        | { step?: number; errors?: FieldErrors }
        | undefined;

      if (detail?.errors) {
        const target = Number(detail.step || targetStep);
        setStep(target);
        setErrors(detail.errors);
        setFailure(
          target !== targetStep
            ? `The server reported a validation error on Step ${target}. Your other drafts have been preserved.`
            : "Please correct the highlighted fields."
        );

        window.setTimeout(() => {
          const firstField = Object.keys(detail.errors || {})[0];
          document.querySelector<HTMLElement>(`[name="${firstField}"]`)?.focus();
        }, 50);
      } else {
        setFailure("Save failed. Your current draft is still available; please retry.");
      }

      setMessage("");
      return false;
    } finally {
      savingRef.current = false;
      setSaving(false);
    }
  }

  async function nextStep() {
    window.clearTimeout(saveTimer.current);

    const success = await saveStep(step);
    if (success && step < 4) {
      setErrors({});
      setStep((current) => current + 1);
    }
  }

  async function finish() {
    window.clearTimeout(saveTimer.current);

    const success = await saveStep(4);
    if (!success) return;

    try {
      await submitAccountSettings(accountId);
      setSubmitted(true);
      setMessage("Account settings submitted successfully.");
    } catch {
      setFailure(
        "The server could not submit the settings. Check that all four steps have been saved."
      );
    }
  }

  if (loading) {
    return <div className="p-8 text-center">Loading account settings...</div>;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/50 p-3 sm:p-6"
      role="dialog"
      aria-modal="true"
      aria-labelledby="settings-title"
    >
      <section className="max-h-[95vh] w-full max-w-2xl overflow-y-auto rounded-2xl bg-white p-5 shadow-2xl sm:p-7">
        <div className="mb-6 flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-wider text-blue-600">
              Account configuration
            </p>
            <h2
              id="settings-title"
              ref={headingRef}
              tabIndex={-1}
              className="mt-1 text-xl font-bold text-slate-900"
            >
              {titles[step - 1]}
            </h2>
            <p className="mt-1 text-sm text-slate-500">
              {accountName} · Account #{accountId}
            </p>
          </div>

          <button
            type="button"
            onClick={onClose}
            aria-label="Close settings"
            className="rounded-lg px-3 py-2 text-slate-500 hover:bg-slate-100"
          >
            ✕
          </button>
        </div>

        <StepIndicator
          currentStep={step}
          completedSteps={completed}
          onStepClick={(target) => {
            window.clearTimeout(saveTimer.current);
            setStep(target);
            setErrors({});
            setFailure("");
          }}
        />

        <div className="my-6">
          <SettingsFields
            step={step}
            draft={draft}
            errors={errors}
            onChange={changeField}
          />
        </div>

        <div aria-live="polite" className="space-y-2">
          {message && (
            <p className="text-sm text-emerald-700">{message}</p>
          )}

          {failure && (
            <div role="alert" className="rounded-lg bg-red-50 p-3 text-sm text-red-800">
              {failure}
            </div>
          )}

          {submitted && (
            <div role="status" className="rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">
              All settings have been submitted.
            </div>
          )}
        </div>

        <div className="mt-7 flex flex-wrap justify-between gap-3 border-t border-slate-200 pt-5">
          <button
            type="button"
            disabled={step === 1 || saving}
            onClick={() => {
              window.clearTimeout(saveTimer.current);
              setStep((current) => current - 1);
              setErrors({});
              setFailure("");
            }}
            className="rounded-lg border border-slate-300 px-4 py-2.5 text-sm disabled:opacity-40"
          >
            Previous
          </button>

          {step < 4 ? (
            <button
              type="button"
              disabled={saving || submitted}
              onClick={nextStep}
              className="rounded-lg bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save & continue"}
            </button>
          ) : (
            <button
              type="button"
              disabled={saving || submitted}
              onClick={finish}
              className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
            >
              {saving ? "Saving..." : "Save & submit"}
            </button>
          )}
        </div>
      </section>
    </div>
  );
}
