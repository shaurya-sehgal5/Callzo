
interface Props {
  currentStep: number;
  completedSteps: number[];
  onStepClick: (step: number) => void;
}

const steps = [
  "Account details",
  "Subscription",
  "Usage limits",
  "Integrations",
];

export default function StepIndicator({
  currentStep,
  completedSteps,
  onStepClick,
}: Props) {
  return (
    <div className="grid grid-cols-4 gap-2">
      {steps.map((label, index) => {
        const step = index + 1;
        const active = currentStep === step;
        const completed = completedSteps.includes(step);

        return (
          <button
            key={step}
            type="button"
            onClick={() => onStepClick(step)}
            aria-current={active ? "step" : undefined}
            className={`rounded-lg border p-2 text-left text-xs sm:p-3 ${
              active
                ? "border-blue-600 bg-blue-50 text-blue-800"
                : completed
                  ? "border-emerald-300 bg-emerald-50 text-emerald-800"
                  : "border-slate-200 bg-white text-slate-500"
            }`}
          >
            <span className="font-bold">{completed ? "✓" : step}</span>
            <span className="mt-1 block hidden sm:block">{label}</span>
          </button>
        );
      })}
    </div>
  );
}
