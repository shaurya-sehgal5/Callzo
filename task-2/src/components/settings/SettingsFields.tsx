
import type { SettingsDraft, FieldErrors } from "../../types/settings";

interface Props {
  step: number;
  draft: SettingsDraft;
  errors: FieldErrors;
  onChange: (field: string, value: string) => void;
}

export default function SettingsFields({
  step,
  draft,
  errors,
  onChange,
}: Props) {
  const inputClass =
    "mt-1 w-full rounded-lg border border-slate-300 px-3 py-2.5 text-sm focus:border-blue-500";

  function field(
    name: string,
    label: string,
    value: string | number,
    type = "text"
  ) {
    return (
      <label className="block text-sm font-medium text-slate-700">
        {label}
        <input
          name={name}
          type={type}
          value={value}
          onChange={(e) => onChange(name, e.target.value)}
          aria-invalid={!!errors[name]}
          aria-describedby={errors[name] ? `${name}-error` : undefined}
          className={`${inputClass} ${errors[name] ? "border-red-500" : ""}`}
        />
        {errors[name] && (
          <span id={`${name}-error`} className="mt-1 block text-xs text-red-600">
            {errors[name]}
          </span>
        )}
      </label>
    );
  }

  if (step === 1) {
    return (
      <div className="space-y-4">
        {field("name", "Account name", draft[1].name)}
        {field("email", "Email address", draft[1].email, "email")}
      </div>
    );
  }

  if (step === 2) {
    return (
      <div className="space-y-4">
        <label className="block text-sm font-medium text-slate-700">
          Subscription plan
          <select
            value={draft[2].plan}
            onChange={(e) => onChange("plan", e.target.value)}
            className={inputClass}
          >
            <option value="">Select a plan</option>
            <option value="basic">Basic</option>
            <option value="pro">Pro</option>
            <option value="enterprise">Enterprise</option>
          </select>
          {errors.plan && (
            <span className="mt-1 block text-xs text-red-600">{errors.plan}</span>
          )}
        </label>

        <label className="block text-sm font-medium text-slate-700">
          Billing country
          <select
            value={draft[2].billing_country}
            onChange={(e) => onChange("billing_country", e.target.value)}
            className={inputClass}
          >
            <option value="">Select a country</option>
            {["US", "IN", "GB", "CA", "AU"].map((country) => (
              <option key={country} value={country}>{country}</option>
            ))}
          </select>
          {errors.billing_country && (
            <span className="mt-1 block text-xs text-red-600">
              {errors.billing_country}
            </span>
          )}
        </label>
      </div>
    );
  }

  if (step === 3) {
    return (
      <div className="space-y-4">
        {field("minutes_cap", "Monthly minutes cap", draft[3].minutes_cap, "number")}
        {field("sms_cap", "Monthly SMS cap", draft[3].sms_cap, "number")}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {field("webhook_url", "Webhook URL", draft[4].webhook_url, "url")}
      <p className="text-xs text-slate-500">
        Optional. Enter a valid HTTP or HTTPS endpoint.
      </p>
    </div>
  );
}
