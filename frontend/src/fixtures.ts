import type { Investigation } from "./api";
import response from "../../contracts/examples/investigation-response.json";

export const sample = response as Investigation;

export const sampleWithoutMemory: Investigation = {
  ...sample,
  run_id: "run-20260630-off",
  memory_mode: "off",
  explanation: {
    ...sample.explanation,
    recalled: [],
    memory_status: "unavailable",
    explanation_source: "template",
    recommendations: sample.explanation.recommendations.map(
      (recommendation) => ({
        ...recommendation,
        action_type: "adjust_policy",
        action:
          "Consider adjusting the acquisition bonus after a measured pilot.",
        history_influence: [],
      }),
    ),
  },
};
