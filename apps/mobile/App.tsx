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

const TABS = { Tutor, Practice, Planner, Cards };

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
