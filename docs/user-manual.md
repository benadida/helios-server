# Helios User Manual

This guide walks through a whole election: creating it, adding voters,
opening it, voting, and publishing the result. The last part is a guide for
voters.

The screenshots come from a test election, "Riverside Club Board Election
2026", with three voters. Your server may offer different login options.

## Part 1: Running an election

### 1. Log in

Log in to your Helios server. Once you're logged in, the home page shows
**create election**, plus the elections you run and the ones you've voted in.

![Home page after logging in](images/manual/admin-home.png)

### 2. Create the election

Click **create election** and fill in the form:

- **Short name:** one word, no spaces. It becomes part of the election's web
  address, for example `/helios/e/club-board-2026`.
- **Name** and **Description:** what voters will see.
- **Type:** Election or Referendum.
- **Use voter aliases:** shows voters as "V12" and so on in the public ballot
  tracking center, instead of their names.
- **Randomize answer order:** shows each voter the answers in a random order.
- **Private?:** only voters on your list can see the election.
- **Help Email Address:** where voters can ask for help.
- **Voting starts at / ends at:** optional, in UTC. Leave them empty to open
  voting as soon as you freeze the election (step 6) and close it yourself.

Click **Next**. You now have the election's page, which always shows the
**Next Step**.

![New election form](images/manual/new-election.png)

### 3. Add questions

Click **questions**. For each question, enter the text, how many answers a
voter may pick ("Select between 0 and 2 answers"), and the answers. Click
**Add Question**.

![Adding a question](images/manual/question-form.png)

You can edit, remove and reorder questions until you freeze the election.

![The finished ballot](images/manual/questions.png)

### 4. Add voters

Click **voters & ballots**. First choose who can vote (you can't change this
after freezing):

- **anyone can vote:** anyone who logs in can vote.
- **only voters listed explicitly below can vote:** only voters you upload.

![Voters page](images/manual/voters-empty.png)

To add voters, click **bulk upload voters** and upload a CSV file, one voter
per line. Most elections use Helios passwords:

```
password,dana,dana@example.org,Dana Lee
password,sam,sam@example.org,Sam Ortiz
password,priya,priya@example.org,Priya Shah
```

The fields are: `password`, a voter ID you choose, the voter's email, and
their name. Helios creates a password for each voter and emails it to them
in step 7. To use a login account instead, put the login type and username,
for example `github,benadida`. If the server has phone login turned on, voters
can also log in with a code texted to them: put `phone` and their number in
international format, for example `phone,+15551234567`. Phone voters can only
be added to an election that uses voter aliases, so that their numbers aren't
published, and their name shows only the last 4 digits, e.g. `+•••••••4567`.

Check the preview and click **Yes, let's go**.

![Checking the upload](images/manual/voters-confirm.png)

The voters are now listed. You can upload more files and remove voters until
you compute the tally, even while voting is open.

![The voter list](images/manual/voters-list.png)

### 5. Trustees (optional)

Trustees hold the keys that decrypt the result. By default Helios is the only
trustee and handles this for you, so you can skip this step.

![Trustees page](images/manual/trustees.png)

For extra protection, add trustees with **add a trustee** (name and email),
then click **send login** to email each one their trustee link. Each trustee
opens the link, clicks **setup your key**, generates a key, saves the secret
key file somewhere safe, and uploads the public key. You can also remove the
Helios trustee, so that no one can decrypt the result without your trustees.

You can't freeze the election until every trustee has uploaded a public key.
Decrypting the result needs every trustee: if one loses their secret key,
the result can't be decrypted.

### 6. Freeze the election

When the ballot and trustees are ready, click **freeze ballot and open
election** under Next Step, then **Freeze the ballot**.

After freezing, the questions, answers and trustees can't change. You can
still change the voter list. Voting opens right away, or at the start time
you set.

![Freezing the ballot](images/manual/freeze.png)

![The election is open](images/manual/election-open.png)

### 7. Contact the voters

On the **voters & ballots** page, click **contact voters**. The **Time to Vote**
template sends each voter the voting link and, for password voters, their
voter ID and password.

The box at the top is a preview. Helios fills in each voter's details in the
fields shown in angle brackets. To add your own text, type it in **Body**;
it appears where `<BODY>` is. Don't paste the preview into it. Choose who to
send to and click **Send**. Phone voters get the message as a text, so use the
**Short** template for them.

![Emailing voters](images/manual/email-voters.png)

Later you can use the same page to remind only the voters who haven't voted
yet.

### 8. While voting is open

The **voters & ballots** page shows how many votes have been cast and each
voter's ballot tracker. If you set an end time, you can **extend voting**
until you compute the tally.

### 9. Close voting and compute the tally

When you're ready to stop voting, click **compute encrypted tally** under
Next Step, then **compute encrypted tally!**. This closes voting: no one can
cast a ballot after this.

![Computing the tally](images/manual/compute-tally.png)

Helios adds up the encrypted ballots without decrypting any of them. If Helios
is a trustee, it decrypts its share automatically. Other trustees now open
their trustee link, click **decrypt with your key**, enter their secret key
and upload their partial decryption.

### 10. Compute and release the result

Once every trustee has decrypted, click **compute results** under Next Step,
then **compute the tally!**. The result is now shown to you only.

![The result, before release](images/manual/results-admin.png)

Check it, then click **release result**. Leave the box checked to email the
voters, and click **release result!**.

![Releasing the result](images/manual/release.png)

Everyone can now see the result on the election page.

![The published result](images/manual/results-public.png)

## Part 2: Voter guide

### 1. Your email

You'll get an email like this one:

```
Dear Dana Lee,

Voting is open until Friday at 5pm.

Election URL (click to begin voting):
https://vote.example.org/helios/e/club-board-2026/vote

Your voter ID: dana
Your password: usyWtLo2yW
```

Keep it: you'll need the voter ID and password to cast your ballot. Some
elections ask you to log in with an account, such as Google or GitHub,
instead.

### 2. Fill in your ballot

Click the link in the email. The voting booth opens. Click **Start**.

![The voting booth](images/manual/booth-start.png)

Select your answers for each question and click **Next** (**Proceed** after
the last question). The booth tells you how many answers you may pick.

![Choosing answers](images/manual/booth-question.png)

### 3. Review and encrypt

The booth shows your choices. Click **[change]** to fix a question.

Your browser then encrypts the ballot and shows your **ballot tracker**, a
long code like `Ag/lQORWPk...`. Write it down or keep the page open. Click
**Proceed to Login**.

![Reviewing the ballot](images/manual/booth-review.png)

**Spoil & Audit** is optional. It lets you check that the booth encrypted
your choices correctly, but that ballot is then thrown away and you start
again. Auditing shows your choices, and if you post the audited ballot,
anyone can see them.

### 4. Cast your ballot

Your ballot isn't cast yet. Enter the voter ID and password from your email
and click **authenticate & cast ballot**.

![Logging in to cast](images/manual/cast-login.png)

Lost your password? Click **Forgot your password? Click here to resend it**.

If you logged in with an account instead, click **CAST this ballot**.

### 5. Done

You'll see **Vote Successfully Cast!** and your ballot tracker. Helios also
emails you the tracker.

![Ballot cast](images/manual/cast-done.png)

### 6. Check your ballot

Open the election page and click **voters & ballots**. Within a few minutes,
your ballot tracker appears next to your name (or your alias). If it matches the one you
wrote down, your ballot was recorded as you cast it.

![Ballot tracking center](images/manual/tracking-center.png)

### Voting again

You can vote again as long as voting is open. Only your last ballot counts.

### Seeing the result

When the administrator releases the result, it appears on the election page,
and you may get an email.
