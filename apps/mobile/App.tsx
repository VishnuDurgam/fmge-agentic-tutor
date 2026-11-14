import AsyncStorage from "@react-native-async-storage/async-storage";
import Constants from "expo-constants";
import { StatusBar } from "expo-status-bar";
import { useEffect, useState } from "react";
import { Pressable, SafeAreaView, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";

const BASE: string = (Constants.expoConfig?.extra as { apiUrl?: string })?.apiUrl || "http://localhost:8000";
let LEARNER = "";

async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  if (!LEARNER) {
    LEARNER = (await AsyncStorage.getItem("learner")) || "";
    if (!LEARNER) {
      LEARNER = Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
      await AsyncStorage.setItem("learner", LEARNER);
    }
  }
  const res = await fetch(BASE + path, { ...init, headers: { "Content-Type": "application/json", "X-Learner-Id": LEARNER } });
  if (!res.ok) throw new Error(await res.text());
  return res.json();
}
const post = (path: string, body: unknown) => api<any>(path, { method: "POST", body: JSON.stringify(body) });

const Btn = ({ t, onPress, alt }: { t: string; onPress: () => void; alt?: boolean }) => (
  <Pressable onPress={onPress} style={[s.btn, alt && s.alt]}><Text style={{ color: alt ? "#14213d" : "#fff" }}>{t}</Text></Pressable>
);

function Tutor() {
  const [q, setQ] = useState(""); const [a, setA] = useState(""); const [busy, setBusy] = useState(false);
  const ask = async () => { setBusy(true); try { setA((await post("/tutor/ask", { question: q })).answer); } catch (e) { setA(String(e)); } setBusy(false); };
  return (<ScrollView contentContainerStyle={s.pad}>
    <TextInput style={s.input} value={q} onChangeText={setQ} placeholder="Ask an FMGE question" multiline />
    <Btn t={busy ? "Thinking..." : "Ask"} onPress={ask} />
    {!!a && <View style={s.card}><Text>{a}</Text></View>}
  </ScrollView>);
}

function Practice() {
  const [q, setQ] = useState<any>(null); const [res, setRes] = useState<any>(null); const [pick, setPick] = useState(-1);
  const load = async () => { setRes(null); setPick(-1); try { setQ(await api("/quiz/next")); } catch { setQ(null); } };
  useEffect(() => { load(); }, []);
  const choose = async (i: number) => { if (res) return; setPick(i); setRes(await post("/quiz/submit", { question_id: q.id, choice: i })); };
  if (!q) return <View style={s.pad}><Text>No questions available.</Text></View>;
  return (<ScrollView contentContainerStyle={s.pad}>
    <Text style={s.muted}>{q.subject} / {q.topic}</Text>
    <Text style={s.bold}>{q.stem}</Text>
    {q.options.map((o: string, i: number) => (
      <Pressable key={i} onPress={() => choose(i)} style={[s.opt, res && i === res.answer && s.good, res && i === pick && i !== res.answer && s.bad]}>
        <Text>{String.fromCharCode(65 + i)}. {o}</Text>
      </Pressable>))}
    {res && <View style={s.card}>
      <Text style={s.bold}>{res.correct ? "Correct" : "Incorrect"}</Text><Text>{res.explanation}</Text>
      {!!res.ai_feedback && <Text>{res.ai_feedback}</Text>}
      {!res.reviewed && <Text style={s.muted}>Draft question, not yet doctor-reviewed.</Text>}
      <Btn t="Next question" onPress={load} />
    </View>}
  </ScrollView>);
}

function Planner() {
  const [date, setDate] = useState(""); const [plan, setPlan] = useState<any>(null);
  const load = () => api("/planner/plan").then(setPlan).catch(() => setPlan(null));
  useEffect(() => { load(); }, []);
  const save = async () => { await api("/planner/profile", { method: "PUT", body: JSON.stringify({ exam_date: date, hours_per_day: 4 }) }); load(); };
  return (<ScrollView contentContainerStyle={s.pad}>
    <TextInput style={s.input} value={date} onChangeText={setDate} placeholder="Exam date YYYY-MM-DD" />
    <Btn t="Build plan" onPress={save} />
    {plan && <View style={s.card}>
      <Text style={s.bold}>{plan.days_left} days left</Text>
      {plan.plan.map((p: any) => <Text key={p.subject}>{p.subject}: {p.days} days</Text>)}
    </View>}
  </ScrollView>);
}

function Cards() {
  const [due, setDue] = useState<any[]>([]); const [flip, setFlip] = useState(false);
  const load = () => api<any[]>("/cards/due").then((d) => { setDue(d); setFlip(false); }).catch(() => {});
  useEffect(() => { load(); }, []);
  const rate = async (quality: number) => { await post(`/cards/${due[0].id}/review`, { quality }); load(); };
  if (!due[0]) return <View style={s.pad}><Text>No cards due. Generate or add cards on the website.</Text></View>;
  return (<ScrollView contentContainerStyle={s.pad}>
    <Text style={s.muted}>{due.length} due</Text>
    <View style={s.card}><Text style={s.bold}>{due[0].front}</Text>{flip && <Text>{due[0].back}</Text>}</View>
    {flip ? <View style={s.row}><Btn alt t="Again" onPress={() => rate(1)} /><Btn alt t="Hard" onPress={() => rate(3)} /><Btn t="Good" onPress={() => rate(4)} /><Btn t="Easy" onPress={() => rate(5)} /></View>
          : <Btn t="Show answer" onPress={() => setFlip(true)} />}
  </ScrollView>);
}

type MQ = { pos: number; id: string; subject: string; stem: string; options: string[]; choice: number | null };

function Mock() {
  const [exam, setExam] = useState<any>(null); const [res, setRes] = useState<any>(null);
  const [i, setI] = useState(0); const [left, setLeft] = useState(0); const [err, setErr] = useState("");
  const finish = async (id: string) => { try { setRes(await post(`/mock/${id}/submit`, {})); await AsyncStorage.removeItem("mock"); } catch (e) { setErr(String(e)); } };
  const load = async (id: string) => {
    const e = await api<any>(`/mock/${id}`);
    if (e.status === "submitted") { setRes(await api(`/mock/${id}/result`)); await AsyncStorage.removeItem("mock"); return; }
    setExam(e); setLeft(e.seconds_left);
  };
  useEffect(() => { AsyncStorage.getItem("mock").then((id) => { if (id) load(id).catch(() => AsyncStorage.removeItem("mock")); }); }, []);
  useEffect(() => { if (!exam || res) return; const t = setInterval(() => setLeft((l) => Math.max(0, l - 1)), 1000); return () => clearInterval(t); }, [exam, res]);
  useEffect(() => { if (exam && !res && left === 0) finish(exam.id); }, [left]);
  const start = async (preset: string) => {
    setErr(""); setRes(null); setI(0);
    try { const e = await post("/mock/start", { preset }); await AsyncStorage.setItem("mock", e.id); setExam(e); setLeft(e.seconds_left); }
    catch (x) { setErr(String(x)); }
  };
  const pick = (q: MQ, k: number) => {
    const next = q.choice === k ? null : k;
    setExam({ ...exam, questions: exam.questions.map((x: MQ) => (x.id === q.id ? { ...x, choice: next } : x)) });
    api(`/mock/${exam.id}/answer`, { method: "PUT", body: JSON.stringify({ question_id: q.id, choice: next }) }).catch((e) => setErr(String(e)));
  };
  const fmt = (n: number) => `${String(Math.floor(n / 60)).padStart(2, "0")}:${String(n % 60).padStart(2, "0")}`;

  if (res) return (<ScrollView contentContainerStyle={s.pad}>
    <View style={s.card}>
      <Text style={s.bold}>{res.score} / {res.total} ({res.percent}%)</Text>
      <Text>{res.passed ? "Pass" : "Below pass mark"} (pass mark {res.pass_mark}, no negative marking)</Text>
      {res.by_subject.map((x: any) => <Text key={x.subject}>{x.subject}: {x.correct}/{x.total}</Text>)}
      <Btn t="New mock" onPress={() => { setRes(null); setExam(null); }} />
    </View>
    {res.review.map((r: any) => (<View key={r.pos} style={s.card}>
      <Text style={s.bold}>{r.pos}. {r.stem}</Text>
      {r.options.map((o: string, k: number) => <Text key={k} style={[s.opt, k === r.answer && s.good, k === r.chosen && k !== r.answer && s.bad]}>{String.fromCharCode(65 + k)}. {o}{k === r.chosen ? " (your answer)" : ""}</Text>)}
      {r.chosen === null && <Text style={s.muted}>Not answered</Text>}
      <Text>{r.explanation}</Text><Text style={s.muted}>Source: {r.source}</Text>
      {!r.reviewed && <Text style={s.muted}>Draft question, not yet doctor-reviewed.</Text>}
    </View>))}
  </ScrollView>);

  if (!exam) return (<ScrollView contentContainerStyle={s.pad}>
    <Text style={s.muted}>FMGE format: 4-option MCQs, 1 mark each, no negative marking, pass at 50%. Explanations appear after you submit.</Text>
    {!!err && <Text style={{ color: "#b91c1c" }}>{err}</Text>}
    <Btn t="Quick test (20 Q, 20 min)" onPress={() => start("quick")} />
    <Btn t="Section (50 Q, 50 min)" onPress={() => start("section")} />
    <Btn t="Part A (150 Q, 150 min)" onPress={() => start("part_a")} />
    <Btn t="Part B (150 Q, 150 min)" onPress={() => start("part_b")} />
  </ScrollView>);

  const q: MQ = exam.questions[i];
  const answered = exam.questions.filter((x: MQ) => x.choice !== null).length;
  return (<ScrollView contentContainerStyle={s.pad}>
    <View style={[s.row, { justifyContent: "space-between" }]}><Text style={s.bold}>Q {i + 1} of {exam.total}</Text><Text style={[s.bold, left < 300 && { color: "#b91c1c" }]}>{fmt(left)}</Text></View>
    {!!err && <Text style={{ color: "#b91c1c" }}>{err}</Text>}
    <Text style={s.muted}>{q.subject}</Text>
    <Text style={s.bold}>{q.stem}</Text>
    {q.options.map((o, k) => (<Pressable key={k} onPress={() => pick(q, k)} style={[s.opt, q.choice === k && s.good]}><Text>{String.fromCharCode(65 + k)}. {o}</Text></Pressable>))}
    <View style={s.row}><Btn alt t="Previous" onPress={() => i > 0 && setI(i - 1)} /><Btn t="Next" onPress={() => i < exam.total - 1 && setI(i + 1)} /></View>
    <Text style={s.muted}>{answered} of {exam.total} answered. Jump to:</Text>
    <View style={s.row}>{exam.questions.map((x: MQ, k: number) => (
      <Pressable key={x.id} onPress={() => setI(k)} style={{ width: 36, padding: 8, alignItems: "center", borderRadius: 6, borderWidth: k === i ? 2 : 1, borderColor: "#14213d", backgroundColor: x.choice !== null ? "#15803d" : "#fff" }}>
        <Text style={{ color: x.choice !== null ? "#fff" : "#14213d" }}>{k + 1}</Text></Pressable>))}</View>
    <Btn t="Submit exam" onPress={() => finish(exam.id)} />
  </ScrollView>);
}

const TABS = { Tutor, Practice, Mock, Planner, Cards };

export default function App() {
  const [tab, setTab] = useState<keyof typeof TABS>("Tutor");
  const Screen = TABS[tab];
  return (<SafeAreaView style={{ flex: 1, backgroundColor: "#f7f8fa" }}>
    <StatusBar style="dark" />
    <View style={{ flex: 1 }}><Screen /></View>
    <View style={s.tabs}>{(Object.keys(TABS) as (keyof typeof TABS)[]).map((k) => (
      <Pressable key={k} onPress={() => setTab(k)} style={{ flex: 1, padding: 14, alignItems: "center" }}>
        <Text style={{ color: k === tab ? "#0f766e" : "#5b6475", fontWeight: k === tab ? "700" : "400" }}>{k}</Text>
      </Pressable>))}</View>
  </SafeAreaView>);
}

const s = StyleSheet.create({
  pad: { padding: 16, gap: 10 }, row: { flexDirection: "row", gap: 8, flexWrap: "wrap" },
  card: { backgroundColor: "#fff", borderRadius: 12, padding: 14, borderWidth: 1, borderColor: "#e2e6ee", gap: 8 },
  input: { backgroundColor: "#fff", borderRadius: 8, padding: 12, borderWidth: 1, borderColor: "#e2e6ee" },
  btn: { backgroundColor: "#0f766e", padding: 12, borderRadius: 8, alignItems: "center" }, alt: { backgroundColor: "#fff", borderWidth: 1, borderColor: "#e2e6ee" },
  opt: { backgroundColor: "#fff", padding: 12, borderRadius: 8, borderWidth: 1, borderColor: "#e2e6ee" },
  good: { borderColor: "#15803d", backgroundColor: "#f0fdf4" }, bad: { borderColor: "#b91c1c", backgroundColor: "#fef2f2" },
  muted: { color: "#5b6475" }, bold: { fontWeight: "700" },
  tabs: { flexDirection: "row", borderTopWidth: 1, borderColor: "#e2e6ee", backgroundColor: "#fff" },
});
