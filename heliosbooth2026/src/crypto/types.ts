/**
 * TypeScript type declarations for the Helios jscrypto library globals.
 * These are loaded via script tags from lib/jscrypto/ and available globally.
 */

// BigInt from lib/jscrypto/bigint.js (wraps sjcl BigInteger)
export interface BigIntType {
  ZERO: BigIntInstance;
  ONE: BigIntInstance;
  TWO: BigIntInstance;
  fromInt(value: number): BigIntInstance;
  fromJSONObject(obj: string): BigIntInstance;
  setup(callback: () => void, errorCallback?: () => void): void;
}

export interface BigIntInstance {
  add(other: BigIntInstance): BigIntInstance;
  subtract(other: BigIntInstance): BigIntInstance;
  multiply(other: BigIntInstance): BigIntInstance;
  mod(modulus: BigIntInstance): BigIntInstance;
  modPow(exponent: BigIntInstance, modulus: BigIntInstance): BigIntInstance;
  modInverse(modulus: BigIntInstance): BigIntInstance;
  equals(other: BigIntInstance): boolean;
  toJSONObject(): string;
  toString(): string;
}

// ElGamal from lib/jscrypto/elgamal.js
export interface ElGamalParams {
  p: BigIntInstance;
  q: BigIntInstance;
  g: BigIntInstance;
}

export interface ElGamalPublicKey {
  p: BigIntInstance;
  q: BigIntInstance;
  g: BigIntInstance;
  y: BigIntInstance;
  toJSONObject(): ElGamalPublicKeyJSON;
}

export interface ElGamalPublicKeyJSON {
  p: string;
  q: string;
  g: string;
  y: string;
}

export interface ElGamalType {
  Params: {
    fromJSONObject(obj: ElGamalParams): ElGamalParams;
  };
  PublicKey: {
    fromJSONObject(obj: ElGamalPublicKeyJSON): ElGamalPublicKey;
  };
}

// Question structure from election JSON
export interface Question {
  question: string;
  short_name: string;
  answers: string[];
  answer_urls?: (string | null)[];
  min: number;
  max: number;
  randomize_answer_order?: boolean;
}

// Election from lib/jscrypto/helios.js
export interface Election {
  uuid: string;
  name: string;
  short_name: string;
  description: string;
  questions: Question[];
  public_key: ElGamalPublicKey;
  cast_url: string;
  frozen_at: string;
  openreg: boolean;
  voters_hash: string | null;
  use_voter_aliases: boolean;
  voting_starts_at: string | null;
  voting_ends_at: string | null;
  election_hash: string;
  hash: string;
  BOGUS_P?: boolean;
  question_answer_orderings?: number[][];
}

export interface EncryptedAnswer {
  toJSONObject(includeRandomness?: boolean): EncryptedAnswerJSON;
}

export interface EncryptedAnswerJSON {
  choices: unknown[];
  individual_proofs: unknown[];
  overall_proof: unknown;
  randomness?: unknown[];
  answer?: number[];
}

export interface EncryptedVote {
  toJSONObject(includeRandomness?: boolean): EncryptedVoteJSON;
  get_hash(): string;
  clearPlaintexts?(): void;
}

export interface EncryptedVoteJSON {
  answers: EncryptedAnswerJSON[];
  election_hash: string;
  election_uuid: string;
}

export interface HELIOSType {
  Election: {
    fromJSONString(raw: string): Election;
    fromJSONObject(obj: unknown): Election;
  };
  EncryptedAnswer: {
    new(question: Question, answer: number[], publicKey: ElGamalPublicKey): EncryptedAnswer;
    fromJSONObject(obj: EncryptedAnswerJSON, election: Election): EncryptedAnswer;
  };
  EncryptedVote: {
    fromEncryptedAnswers(election: Election, answers: EncryptedAnswer[]): EncryptedVote;
  };
  get_bogus_public_key(): ElGamalPublicKey;
}

export interface RandomType {
  getRandomInteger(max: BigIntInstance): BigIntInstance;
}

export interface UTILSType {
  array_remove_value<T>(arr: T[], val: T): T[];
  PROGRESS: new () => {
    n_ticks: number;
    current_tick: number;
    addTicks(n: number): void;
    tick(): void;
    progress(): number;
  };
  object_sort_keys<T extends object>(obj: T): T;
}

// Election metadata from server
export interface ElectionMetadata {
  help_email: string;
  randomize_answer_order?: boolean;
  use_advanced_audit_features?: boolean;
}

// Worker message types
export interface WorkerSetupMessage {
  type: 'setup';
  election: string;
}

export interface WorkerEncryptMessage {
  type: 'encrypt';
  q_num: number;
  answer: number[];
  id: number;
}

export type WorkerInMessage = WorkerSetupMessage | WorkerEncryptMessage;

export interface WorkerLogMessage {
  type: 'log';
  msg: string;
}

export interface WorkerResultMessage {
  type: 'result';
  q_num: number;
  encrypted_answer: EncryptedAnswerJSON;
  id: number;
}

export type WorkerOutMessage = WorkerLogMessage | WorkerResultMessage;

// BALLOT helper (from helios.js)
export interface BALLOTType {
  pretty_choices(election: Election, ballot: { answers: number[][] }): string[][];
}

// Declare non-conflicting crypto globals that will be available after script loading
// BigInt must use (window as any).BigInt due to conflict with TypeScript's built-in BigInt type
declare global {
  const HELIOS: HELIOSType;
  const ElGamal: ElGamalType;
  const Random: RandomType;
  const UTILS: UTILSType;
  const BALLOT: BALLOTType;
  const sjcl: {
    random: {
      startCollectors(): void;
      addEntropy(data: string): void;
    };
  };
  function b64_sha256(data: string): string;
}
