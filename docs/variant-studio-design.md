# Variant Studio — design brief

A screen in the existing question-bank app where a teacher picks a bank question, generates verified variants
(answer, worked solution, tricky options), and accepts the ones they want.

Existing frontend stack (checked): **React 18 + Vite + Tailwind 3 + KaTeX + lucide-react**.
Everything below is chosen to fit that stack with no rewrite.

---

## 1. Final recommendation (my pick)

| Area | Pick | Why |
|---|---|---|
| Components | **shadcn/ui** (copy-in, Tailwind-based, Radix underneath) | Fits Tailwind as-is; accessible; you own the code |
| Colours | **Radix Colors**: `slate` neutrals, `indigo` accent, `grass` correct, `amber` trap, `tomato` error | Scales built for contrast in light and dark |
| Motion | **Motion** (`motion/react`, the successor to Framer Motion) | Smooth layout animations, staggered reveals, spring physics |
| Icons | **lucide-react** (already installed) | No new dependency |
| Type | **Geist** for UI text, **Geist Mono** for numbers/IDs, **KaTeX** (already installed) for maths | Clean, modern, excellent digits |
| Toasts | **sonner** | Small, smooth, matches shadcn |
| Keyboard shortcuts | **react-hotkeys-hook** | Teachers review fast with A / R / arrow keys |
| Mood | "Linear meets Brilliant": calm workspace, a few wow moments | Teachers use it for hours; wow only where it carries meaning |

The rest of this file is reference: inspiration sources, the layout, and the detailed rules.

---

## 2. Where to look for inspiration

- **Mobbin** (mobbin.com): real app screens. Search *quiz*, *flashcards*, *review queue*.
- **Godly** (godly.website), **Awwwards**: motion and visual ideas.
- **Dribbble / Behance**: search *edtech dashboard*, *quiz UI*. Take ideas, not layouts.
- **Product benchmarks for feel**: Linear, Vercel, Stripe, Raycast, Arc.
- **Learning benchmarks for feedback**: Brilliant.org, Duolingo.

---

## 3. Layout

### 3a. Bank list (existing page): add one button

```
┌──────────────────────────────────────────────────────────┐
│ Rotational Motion · JEE Main 2023                        │
│ A ring rolls down a rough incline of 30°...              │
│ (A) ...  (B) ...  (C) ...  (D) ...                       │
│                                   [ ✦ Make variants ]    │
└──────────────────────────────────────────────────────────┘
```
The button appears only when a verified pattern exists for the question. Otherwise a muted "No variants yet" label shows.

### 3b. Variant Studio

```
┌─ Original (sticky) ──┐  ┌─ Variant 1 ───────────────── ✓ Verified ─┐
│ Ring on 30° incline, │  │ A solid sphere is released on a rough    │
│ minimum μ = ?        │  │ 37° incline. Minimum μ to roll?          │
│                      │  │                                          │
│ Pattern:             │  │ ○ A  3/14   trap: sliding-block tan θ    │
│ Rolling + friction   │  │ ● B  6/35   ✓ correct                    │
│                      │  │ ○ C  3/4    trap: sin and cos swapped    │
│ Vary:                │  │ ○ D  9/35   trap: wrong moment of inertia│
│ [x] numbers          │  │                                          │
│ [x] body / species   │  │ ▸ Show solution                          │
│ [ ] quantity asked   │  │                                          │
│ Difficulty  ●●○      │  │ [A] Accept   [R] Reject   [M] More like  │
│ [ Generate 5 more ]  │  └──────────────────────────────────────────┘
└──────────────────────┘  ┌─ Variant 2 … ────────────────────────────┐

┌─ Tray ───────────────────────────────────────────────────────────────┐
│ 3 selected   ▢▢▢                          [ Save to bank (pending) ] │
└──────────────────────────────────────────────────────────────────────┘
```

- Desktop: two columns (original 320px sticky | variants fluid). Tray docked at the bottom.
- Phone (<640px): one column. The original collapses to a header strip; the tray becomes a bottom sheet.

---

## 4. Colour and contrast

- Background `slate-1`, cards `white` / `slate-2` (dark: `slate-2` / `slate-3`), borders `slate-6`.
- One accent only: `indigo-9` for primary buttons and focus rings.
- Meaning colours, always paired with an icon or word (never colour alone):
  - correct → `grass-9` + ✓
  - trap / wrong option → `amber-11` text on `amber-3`
  - failed / refused → `tomato-11`
- Body text at least **4.5:1** contrast, large text at least 3:1 (check with the WebAIM contrast checker).
- Dark mode from day one, via Radix dark scales and Tailwind `dark:`.

## 5. Motion (subtle by default, wow in three places)

| Moment | Animation | Duration |
|---|---|---|
| **Generate** (wow) | Skeleton cards appear, then real cards replace them one by one (stagger 80 ms) | 200 ms each |
| **Verified** (wow) | Badge changes from "checking…" to "✓ Verified" with a small scale pop | 180 ms |
| **Accept** (wow) | Card shrinks and flies into the tray (shared-layout animation); tray count ticks up | 300 ms spring |
| Show solution | Height expand + fade | 200 ms ease-out |
| Hover on card/button | Lift by 2 px, shadow deepens | 150 ms |
| Reject | Fade + collapse | 180 ms |

- Respect `prefers-reduced-motion`: replace movement with simple fades.
- Never animate layout while the teacher is reading; nothing auto-moves.

## 6. Cursor, interaction, feel

- `cursor-pointer` only on clickable things; text stays selectable.
- Buttons: hover tint, **instant** pressed state (scale 0.98), visible focus ring (`indigo-8`, 2 px).
- Keyboard: `A` accept · `R` reject · `M` more like this · `S` toggle solution · `J`/`K` next/previous card · `G` generate.
  A `?` key shows the shortcut list.
- Optimistic UI: accepting updates the tray instantly; it rolls back with a toast if the save fails.

## 7. Smoothness and performance

- Skeleton cards while generating; the layout never jumps (reserve card heights).
- Render KaTeX once per card and memoise it.
- Generation endpoint streams variants as they verify, so the first card shows in under a second.
- Lazy-load the studio route.

## 8. Question card anatomy

1. Top row: variant number · difficulty dots · badge (`✓ Verified` / `Needs teacher check`)
2. Stem (KaTeX), max width 68 characters per line
3. Options A–D: letter chip + value. The correct option has a green left bar; each wrong option has an amber "trap:" note
   (the student mistake it catches, in plain words)
4. "Show solution" collapsible: worked steps, final answer highlighted
5. Actions: Accept · Reject · More like this

## 9. Rules that never bend

- A variant that failed verification is **never shown**.
- Questions without a pattern show "No verified variants yet". Nothing is guessed.
- Saved variants go in as **PENDING_REVIEW**; nothing goes live without approval.

## 10. Build order

1. Backend endpoint: `POST /api/variants { questionId, n, vary, difficulty }`, which calls the generator and streams back verified variants.
2. Question → pattern index, so the button appears only where variants exist.
3. Variant Studio page: layout, cards, solution, tray.
4. Motion and keyboard shortcuts.
5. Dark mode and phone layout pass.

---

### Your changes

Edit anything above, or note changes here, and hand the file back.

-
