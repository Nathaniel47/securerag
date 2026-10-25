# Question review summary

Reviewed all 150 generated questions in `results/questions_review.csv` against their source chunks
(`data/chunks.jsonl`). Result written to `results/questions_review_reviewed.csv` (160 rows).

| Outcome | Rows | Meaning |
|---|---|---|
| Kept as is | 67 | Answer supported, question stands alone |
| Kept, rewritten for specificity | 61 | A name or context added (bare surnames, "the school", "he"); answer unchanged except trimming |
| Kept, substantive rewrite | 12 | What is asked or the answer changed |
| Rejected (keep = n) | 10 | Ambiguous answer, garbled source, trivial or not scorable |
| Replacements added | 10 | New questions q150-q159, one per rejection |

**Final set: 150 questions with keep = y** (67 + 61 + 12 + 10).
No duplicates found: no two questions share an answer, and the similar-looking pairs (for example
q066 and q067) ask about different facts.

## Examples

- **Rewritten, name added:** q008 "What law firm did Gyimah work for as an associate?" became "... did Kwasi Anokye Gyimah work for ...".
  q017 "Bawumia" became "Mumuni Bawumia".
- **Rewritten, substantive:** q077 asked how many English Constitution Lodges *joined* the Grand Lodge of Ghana
  with answer "57", but the source says none of the 57 joined; it now asks how many did not join.
  q141 asked where e.tv Ghana is "headquartered", but the source only says it broadcasts from Accra.
- **Rejected:** q058 (two majors planned the coup, so two valid answers), q136 (answer is an IPA symbol that the
  scorer's normaliser strips, so almost any answer would match), q145 (asks for four institutions, answer lists one).
- **Replaced:** q150 "In what year was the Foundation for Contemporary Art (FCA) in Ghana founded?" -> 2004.

## Things to know

- **Excel damaged the working CSV.** Your edited copy had 22 answers turned into short dates
  (for example "4 April 1944" became "04-Apr-44", "January 7" became "Jan-07").
  I rebuilt the file from `data/questions.jsonl`, which has the originals,
  and kept all your keep/corrected_question entries. To avoid this, open the CSV via Excel's text import
  with the columns set to Text, or edit in a text editor.
- **Your edits I changed:** q040 and q041 (your rewrites were kept but fixed, see notes), and q046 (you marked y;
  I set n because there are many valid answers). q057 has two valid answers (Roman Catholic and Pentecostal);
  I left it as a rewrite but you may want to reject it.
- **Evidence column is sometimes the wrong sentence** (q000, q027, q099, q105, q117, q124, q130). The answers are
  supported elsewhere in the same chunk; the right sentence is quoted in each row's notes. This is a bug in
  `evidence_sentence()` in `securerag/eval/questions.py`, which takes the first sentence containing the answer text.
- `data/questions.jsonl` is unchanged and nothing is marked `hand_checked`. The corrections and the 10 replacements
  still need to be merged into it once you have confirmed.

## Spot-check list (20 rows)

You asked for every rewrite plus a random sample, but there are 73 rewrites, which is more than 20.
This list takes all the substantive ones and the one override, 3 of the numeric replacements, and 4 random
unchanged rows (seed 42). The 61 name-only rewrites are tagged `REWRITE-NAME` in the notes column if you want to scan them.

| id | why | question (corrected if rewritten) | answer |
|---|---|---|---|
| q013 | substantive rewrite | Which amendment rules (CI 133) were passed in 2020 as an outcome of the BEEP project's work within Ghana's Judiciary? | High Court (Civil Procedure) Amendment Rules 2020 |
| q040 | substantive rewrite | In which year did a Yale University study find that prayer camp staff and psychiatric hospital mental health professionals were interested in collaborating, according to the article on disability in Ghana? | 2016 |
| q041 | substantive rewrite | What term is used for the religious alternative medicine institutes in Ghana that replace hospital care for people with serious neuropsychiatric illness? | Prayer camps |
| q046 | rejected, overriding your y | Which postgraduate degree is listed under the university’s accredited programmes? | Master of Business Administration (MBA) |
| q061 | substantive rewrite | On what date was the referendum held that adopted Ghana's fourth constitution? | April 28, 1992 |
| q077 | substantive rewrite | How many English Constitution Lodges in Ghana did not join the Grand Lodge of Ghana? | 57 |
| q083 | substantive rewrite | What governs Ghana's current property rights system, together with several regional customary policies? | the Land Bill of 2016 |
| q099 | substantive rewrite | Which party did Afieye Ashong represent when winning the Kpone Katamanso seat in 1996? | National Democratic Congress |
| q105 | substantive rewrite | Which member of Ghana's Provisional National Defence Council was executed for his involvement in the murder of three senior judges and a retired army officer? | Joachim Amartey Quaye |
| q117 | substantive rewrite | Which vigilante group loyal to the government stormed the circuit court in Kumasi? | Delta Force |
| q137 | substantive rewrite | What kind of dialect is Ghanaian English, which is notable for not presenting linking or intrusive R? | non-rhotic |
| q141 | substantive rewrite | From which city does e.tv Ghana broadcast? | Accra |
| q142 | substantive rewrite | In which city did Josiah Ofori Boateng begin his legal career as an Assistant State Attorney? | Sekondi-Takoradi |
| q151 | new replacement | How much International Development Association credit did the World Bank approve in October 2020 to help establish Development Bank Ghana? | US$250 million |
| q154 | new replacement | What were the total assets of Republic Bank (Ghana) PLC as of March 2020? | GHS:3.377 billion |
| q157 | new replacement | In which year was the first report of illegal cannabis cultivation in Ghana? | 1960 |
| q009 | random kept row | What is the main ingredient of Aprapransa? | roasted corn flour |
| q033 | random kept row | Where was Catherine Mulgrave born? | Luanda, Angola |
| q068 | random kept row | In what year was American Sign Language brought to Bolivia? | 1973 |
| q084 | random kept row | On what date are Ghana's presidential and parliamentary elections typically held? | 7 December |
