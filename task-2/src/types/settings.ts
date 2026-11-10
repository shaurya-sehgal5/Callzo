
export interface Step1Data {
  name: string;
  email: string;
}

export interface Step2Data {
  plan: "basic" | "pro" | "enterprise" | "";
  billing_country: "US" | "IN" | "GB" | "CA" | "AU" | "";
}

export interface Step3Data {
  minutes_cap: number | "";
  sms_cap: number | "";
}

export interface Step4Data {
  webhook_url: string;
}

export interface SettingsDraft {
  1: Step1Data;
  2: Step2Data;
  3: Step3Data;
  4: Step4Data;
}

export interface FieldErrors {
  [field: string]: string;
}

export interface SettingsValidationError {
  detail?: {
    step?: number;
    errors?: FieldErrors;
  };
}

export const emptyDraft: SettingsDraft = {
  1: { name: "", email: "" },
  2: { plan: "", billing_country: "" },
  3: { minutes_cap: "", sms_cap: "" },
  4: { webhook_url: "" },
};
