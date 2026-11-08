// The on-device assistant: a small language model that runs inside the
// browser (WebGPU, via WebLLM). The weights are downloaded once and kept in
// the browser's cache; after that no network is needed and nothing typed
// here leaves the device.

export interface OfflineModel {
  id: string;
  /** Approximate download size, shown before the user commits to it. */
  sizeMb: number;
}

// Both are multilingual. The smaller one is for phones with little memory.
export const OFFLINE_MODELS: Record<"small" | "standard", OfflineModel> = {
  small: { id: "Qwen2.5-0.5B-Instruct-q4f16_1-MLC", sizeMb: 400 },
  standard: { id: "Qwen2.5-1.5B-Instruct-q4f16_1-MLC", sizeMb: 1000 },
};

export type OfflineModelKey = keyof typeof OFFLINE_MODELS;

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
}

// A short version of Francessca's rules. Small models follow few, plain
// instructions far better than a long policy.
export const OFFLINE_SYSTEM_PROMPT = `You are Francessca, an assistant that helps a person get organised before they speak with a lawyer in Germany.
Rules:
- You are NOT a lawyer. Never give legal advice, never predict outcomes, never say what the person should do legally.
- Your job is to collect facts: what happened, when, who was involved, which documents exist, what deadlines were mentioned.
- Ask ONE short question at a time. Wait for the answer before asking the next.
- Be warm and plain. No legal jargon.
- Always reply in the language the person writes in.
- When asked, summarise the facts so far as a short list the person can show a lawyer.`;

export function webGpuAvailable(): boolean {
  return typeof navigator !== "undefined" && "gpu" in navigator;
}

type Engine = {
  chat: {
    completions: {
      create: (args: {
        messages: { role: string; content: string }[];
        stream: true;
        temperature?: number;
        max_tokens?: number;
      }) => Promise<AsyncIterable<{ choices: { delta?: { content?: string | null } }[] }>>;
    };
  };
  interruptGenerate: () => void;
  unload: () => Promise<void>;
};

let engine: Engine | null = null;
let loadedModel: string | null = null;

/** Whether the weights are already on this device. */
export async function isModelDownloaded(key: OfflineModelKey): Promise<boolean> {
  try {
    const webllm = await import("@mlc-ai/web-llm");
    return await webllm.hasModelInCache(OFFLINE_MODELS[key].id);
  } catch {
    return false;
  }
}

/** Download (first time) and start the model. `onProgress` gets 0..1. */
export async function loadModel(
  key: OfflineModelKey,
  onProgress: (fraction: number, text: string) => void,
): Promise<void> {
  const { id } = OFFLINE_MODELS[key];
  if (engine && loadedModel === id) return;
  const webllm = await import("@mlc-ai/web-llm");
  if (engine) await engine.unload().catch(() => {});
  engine = (await webllm.CreateMLCEngine(id, {
    initProgressCallback: (report) => onProgress(report.progress, report.text),
  })) as unknown as Engine;
  loadedModel = id;
}

export async function deleteModel(key: OfflineModelKey): Promise<void> {
  const { id } = OFFLINE_MODELS[key];
  if (engine && loadedModel === id) {
    await engine.unload().catch(() => {});
    engine = null;
    loadedModel = null;
  }
  const webllm = await import("@mlc-ai/web-llm");
  await webllm.deleteModelAllInfoInCache(id);
}

export function isModelLoaded(): boolean {
  return engine !== null;
}

export function stopGenerating(): void {
  engine?.interruptGenerate();
}

/** Stream a reply. `onToken` receives the text so far, not the increment. */
export async function generateReply(
  history: ChatTurn[],
  onToken: (textSoFar: string) => void,
): Promise<string> {
  if (!engine) throw new Error("Model not loaded");
  // Small context window: the system prompt plus the most recent turns.
  const recent = history.slice(-12);
  const stream = await engine.chat.completions.create({
    messages: [{ role: "system", content: OFFLINE_SYSTEM_PROMPT }, ...recent],
    stream: true,
    temperature: 0.4,
    max_tokens: 400,
  });
  let text = "";
  for await (const chunk of stream) {
    text += chunk.choices[0]?.delta?.content ?? "";
    onToken(text);
  }
  return text;
}
