/**
 * Lutervyn IDE — JavaScript Syntax Highlighting Test
 * ===================================================
 * Covers: variables, functions, classes, async/await, promises,
 * template literals, destructuring, modules, generators, proxies,
 * symbols, iterators, closures, regex, error handling, DOM, etc.
 */

// ══════════════════════════════════════════════════════════════
// IMPORTS & EXPORTS
// ══════════════════════════════════════════════════════════════
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { createServer } from 'http';
import fs from 'fs/promises';
import path from 'path';
import EventEmitter from 'events';
export default class AppController {};
export { AppController as Controller };
export const VERSION = '2.0.0';

// ══════════════════════════════════════════════════════════════
// VARIABLES & CONSTANTS
// ══════════════════════════════════════════════════════════════
const MAX_RETRIES = 3;
const PI = 3.14159265358979;
const EULER = 2.71828182845;
let counter = 0;
var legacyVar = 'old style';
const HEX = 0xFF00FF;
const OCTAL = 0o755;
const BINARY = 0b10101010;
const BIG_INT = 9007199254740991n;
const SCIENTIFIC = 6.022e23;
const NEGATIVE_EXP = 1.6e-19;
const INFINITY_VAL = Infinity;
const NAN_VAL = NaN;
const NULL_VAL = null;
const UNDEF_VAL = undefined;
const BOOL_TRUE = true;
const BOOL_FALSE = false;

// ══════════════════════════════════════════════════════════════
// STRINGS — all types
// ══════════════════════════════════════════════════════════════
const singleQuoted = 'Hello, World!';
const doubleQuoted = "Hello, World!";
const templateLiteral = `Hello, ${singleQuoted}! Count is ${counter + 1}`;
const multilineTemplate = `
    This is a multiline
    template literal with
    expressions: ${2 ** 10} and ${Math.PI.toFixed(4)}
`;
const escapedString = "Line 1\nLine 2\tTabbed\"Quoted\"";
const rawRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/gi;
const taggedTemplate = String.raw`C:\Users\Documents\file.txt`;

// ══════════════════════════════════════════════════════════════
// FUNCTIONS — declarations, expressions, arrows
// ══════════════════════════════════════════════════════════════
function fibonacci(n) {
    if (n <= 1) return n;
    return fibonacci(n - 1) + fibonacci(n - 2);
}

const factorial = function(n) {
    if (n === 0) return 1;
    return n * factorial(n - 1);
};

const add = (a, b) => a + b;
const multiply = (a, b) => {
    const result = a * b;
    console.log(`${a} * ${b} = ${result}`);
    return result;
};

const identity = x => x;
const noop = () => {};
const getObject = () => ({ key: 'value', nested: { a: 1 } });

// Default parameters & rest/spread
function createUser(name, age = 25, ...roles) {
    return { name, age, roles, createdAt: new Date() };
}

function sum(...numbers) {
    return numbers.reduce((acc, n) => acc + n, 0);
}

// ══════════════════════════════════════════════════════════════
// CLASSES — full ES6+ class syntax
// ══════════════════════════════════════════════════════════════
class EventBus extends EventEmitter {
    #listeners = new Map();       // Private field
    #maxListeners = 100;
    static instanceCount = 0;     // Static field

    constructor(options = {}) {
        super();
        this.name = options.name || 'default';
        this.debug = options.debug ?? false;
        EventBus.instanceCount++;
    }

    // Public method
    on(event, callback) {
        if (!this.#listeners.has(event)) {
            this.#listeners.set(event, new Set());
        }
        this.#listeners.get(event).add(callback);
        return this;
    }

    // Private method
    #validateEvent(event) {
        if (typeof event !== 'string') {
            throw new TypeError(`Event must be a string, got ${typeof event}`);
        }
        return true;
    }

    emit(event, ...args) {
        this.#validateEvent(event);
        const listeners = this.#listeners.get(event);
        if (!listeners) return false;

        for (const listener of listeners) {
            try {
                listener.apply(this, args);
            } catch (error) {
                console.error(`Error in listener for "${event}":`, error);
            }
        }
        return true;
    }

    // Getter & Setter
    get listenerCount() {
        let total = 0;
        for (const [, set] of this.#listeners) {
            total += set.size;
        }
        return total;
    }

    set maxListeners(value) {
        if (value < 0) throw new RangeError('maxListeners must be non-negative');
        this.#maxListeners = value;
    }

    // Static method
    static create(options) {
        return new EventBus(options);
    }

    // Symbol iterator
    [Symbol.iterator]() {
        const events = [...this.#listeners.keys()];
        let index = 0;
        return {
            next() {
                if (index < events.length) {
                    return { value: events[index++], done: false };
                }
                return { done: true };
            }
        };
    }

    // toString
    [Symbol.toPrimitive](hint) {
        if (hint === 'string') return `EventBus(${this.name})`;
        if (hint === 'number') return this.listenerCount;
        return true;
    }
}

// ══════════════════════════════════════════════════════════════
// INHERITANCE & MIXINS
// ══════════════════════════════════════════════════════════════
class Animal {
    constructor(name, sound) {
        this.name = name;
        this.sound = sound;
    }

    speak() {
        return `${this.name} says ${this.sound}!`;
    }
}

class Dog extends Animal {
    constructor(name, breed) {
        super(name, 'Woof');
        this.breed = breed;
    }

    fetch(item) {
        return `${this.name} fetches the ${item}`;
    }
}

// Mixin pattern
const Serializable = (Base) => class extends Base {
    toJSON() {
        return JSON.stringify(this);
    }

    static fromJSON(json) {
        return Object.assign(new this(), JSON.parse(json));
    }
};

class SerializableDog extends Serializable(Dog) {
    constructor(name, breed) {
        super(name, breed);
    }
}

// ══════════════════════════════════════════════════════════════
// ASYNC / AWAIT / PROMISES
// ══════════════════════════════════════════════════════════════
async function fetchData(url) {
    try {
        const response = await fetch(url);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        const data = await response.json();
        return data;
    } catch (error) {
        console.error(`Failed to fetch ${url}:`, error.message);
        throw error;
    } finally {
        console.log('Fetch attempt completed');
    }
}

const fetchWithRetry = async (url, retries = MAX_RETRIES) => {
    for (let attempt = 1; attempt <= retries; attempt++) {
        try {
            return await fetchData(url);
        } catch (error) {
            if (attempt === retries) throw error;
            const delay = Math.pow(2, attempt) * 1000;
            await new Promise(resolve => setTimeout(resolve, delay));
        }
    }
};

function delay(ms) {
    return new Promise((resolve, reject) => {
        if (ms < 0) reject(new Error('Delay must be positive'));
        setTimeout(resolve, ms);
    });
}

// Promise combinators
async function parallelFetch(urls) {
    const results = await Promise.all(urls.map(url => fetchData(url)));
    const settled = await Promise.allSettled(urls.map(url => fetchData(url)));
    const fastest = await Promise.race(urls.map(url => fetchData(url)));
    const firstSuccess = await Promise.any(urls.map(url => fetchData(url)));
    return { results, settled, fastest, firstSuccess };
}

// ══════════════════════════════════════════════════════════════
// GENERATORS & ITERATORS
// ══════════════════════════════════════════════════════════════
function* range(start, end, step = 1) {
    for (let i = start; i < end; i += step) {
        yield i;
    }
}

function* fibonacciGenerator() {
    let [a, b] = [0, 1];
    while (true) {
        yield a;
        [a, b] = [b, a + b];
    }
}

async function* asyncRange(start, end) {
    for (let i = start; i < end; i++) {
        await delay(10);
        yield i;
    }
}

// Using generators
const numbers = [...range(0, 20, 2)];
const fib = fibonacciGenerator();
const first10Fibs = Array.from({ length: 10 }, () => fib.next().value);

// ══════════════════════════════════════════════════════════════
// DESTRUCTURING & SPREAD
// ══════════════════════════════════════════════════════════════
const [first, second, ...rest] = [1, 2, 3, 4, 5];
const { name: userName, age: userAge = 30, ...otherProps } = { name: 'Alice', age: 28, role: 'admin' };

// Nested destructuring
const { data: { users: [firstUser, ...otherUsers] } } = {
    data: { users: [{ id: 1, name: 'Bob' }, { id: 2, name: 'Carol' }] }
};

// Spread operator
const arr1 = [1, 2, 3];
const arr2 = [4, 5, 6];
const merged = [...arr1, ...arr2, 7, 8, 9];

const obj1 = { a: 1, b: 2 };
const obj2 = { c: 3, d: 4 };
const mergedObj = { ...obj1, ...obj2, e: 5 };

// ══════════════════════════════════════════════════════════════
// PROXY & REFLECT
// ══════════════════════════════════════════════════════════════
const handler = {
    get(target, property, receiver) {
        console.log(`Getting ${String(property)}`);
        return Reflect.get(target, property, receiver);
    },
    set(target, property, value, receiver) {
        console.log(`Setting ${String(property)} = ${value}`);
        if (typeof value === 'number' && value < 0) {
            throw new RangeError('Value must be non-negative');
        }
        return Reflect.set(target, property, value, receiver);
    },
    has(target, property) {
        return Reflect.has(target, property);
    },
    deleteProperty(target, property) {
        console.log(`Deleting ${String(property)}`);
        return Reflect.deleteProperty(target, property);
    }
};

const reactiveObject = new Proxy({ count: 0, name: 'test' }, handler);

// ══════════════════════════════════════════════════════════════
// SYMBOLS & WEAKREF
// ══════════════════════════════════════════════════════════════
const uniqueId = Symbol('id');
const globalSym = Symbol.for('app.global');
const symDescription = Symbol('description').description;

const objWithSymbol = {
    [uniqueId]: 12345,
    [Symbol.toPrimitive](hint) {
        if (hint === 'number') return 42;
        return 'symbolic object';
    }
};

const weakRef = new WeakRef({ data: 'temporary' });
const registry = new FinalizationRegistry((heldValue) => {
    console.log(`Object with key "${heldValue}" was garbage collected`);
});

// ══════════════════════════════════════════════════════════════
// MAP, SET, WEAKMAP, WEAKSET
// ══════════════════════════════════════════════════════════════
const userMap = new Map([
    ['alice', { id: 1, role: 'admin' }],
    ['bob', { id: 2, role: 'user' }],
    ['carol', { id: 3, role: 'moderator' }]
]);

const uniqueSet = new Set([1, 2, 3, 2, 1, 4, 5]);
const weakMap = new WeakMap();
const weakSet = new WeakSet();

for (const [key, value] of userMap.entries()) {
    console.log(`${key}: ${JSON.stringify(value)}`);
}

// ══════════════════════════════════════════════════════════════
// ERROR HANDLING — Custom errors
// ══════════════════════════════════════════════════════════════
class AppError extends Error {
    constructor(message, code, details = {}) {
        super(message);
        this.name = 'AppError';
        this.code = code;
        this.details = details;
        this.timestamp = new Date().toISOString();
        Error.captureStackTrace?.(this, AppError);
    }
}

class ValidationError extends AppError {
    constructor(field, message) {
        super(`Validation failed for "${field}": ${message}`, 'VALIDATION_ERROR');
        this.name = 'ValidationError';
        this.field = field;
    }
}

class NotFoundError extends AppError {
    constructor(resource, id) {
        super(`${resource} with id "${id}" not found`, 'NOT_FOUND', { resource, id });
        this.name = 'NotFoundError';
    }
}

function riskyOperation() {
    try {
        const data = JSON.parse('{"valid": true}');
        if (!data.valid) throw new ValidationError('data', 'Invalid data format');
        return data;
    } catch (error) {
        if (error instanceof ValidationError) {
            console.warn(`Validation: ${error.message}`);
        } else if (error instanceof SyntaxError) {
            console.error('JSON parsing failed');
        } else {
            throw error;
        }
    } finally {
        console.log('Operation completed');
    }
}

// ══════════════════════════════════════════════════════════════
// CLOSURES & HIGHER ORDER FUNCTIONS
// ══════════════════════════════════════════════════════════════
function createCounter(initial = 0) {
    let count = initial;
    return {
        increment: () => ++count,
        decrement: () => --count,
        reset: () => { count = initial; },
        get value() { return count; }
    };
}

function compose(...fns) {
    return (x) => fns.reduceRight((acc, fn) => fn(acc), x);
}

function pipe(...fns) {
    return (x) => fns.reduce((acc, fn) => fn(acc), x);
}

function curry(fn) {
    return function curried(...args) {
        if (args.length >= fn.length) {
            return fn.apply(this, args);
        }
        return (...moreArgs) => curried(...args, ...moreArgs);
    };
}

function memoize(fn) {
    const cache = new Map();
    return function(...args) {
        const key = JSON.stringify(args);
        if (cache.has(key)) return cache.get(key);
        const result = fn.apply(this, args);
        cache.set(key, result);
        return result;
    };
}

const memoizedFib = memoize(fibonacci);

// ══════════════════════════════════════════════════════════════
// ARRAY & OBJECT METHODS
// ══════════════════════════════════════════════════════════════
const data = [
    { name: 'Alice', age: 30, score: 95 },
    { name: 'Bob', age: 25, score: 82 },
    { name: 'Carol', age: 35, score: 91 },
    { name: 'Dave', age: 28, score: 88 },
    { name: 'Eve', age: 22, score: 97 },
];

const processed = data
    .filter(person => person.age >= 25)
    .map(person => ({
        ...person,
        grade: person.score >= 90 ? 'A' : person.score >= 80 ? 'B' : 'C',
        label: `${person.name} (${person.age})`
    }))
    .sort((a, b) => b.score - a.score)
    .reduce((acc, person) => {
        acc[person.grade] = acc[person.grade] || [];
        acc[person.grade].push(person);
        return acc;
    }, {});

const flatData = [[1, 2], [3, [4, 5]], [6]].flat(Infinity);
const entries = Object.entries(mergedObj);
const fromEntries = Object.fromEntries(entries);
const frozen = Object.freeze({ immutable: true, nested: { still: 'mutable' } });

// ══════════════════════════════════════════════════════════════
// REGEX PATTERNS
// ══════════════════════════════════════════════════════════════
const emailRegex = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;
const urlRegex = /https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)/;
const phoneRegex = /^\+?(\d{1,3})?[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}$/;

const text = "Contact us at hello@example.com or visit https://example.com";
const matches = text.match(emailRegex);
const replaced = text.replace(urlRegex, '[URL]');
const groups = "2024-01-15".match(/(?<year>\d{4})-(?<month>\d{2})-(?<day>\d{2})/);

// ══════════════════════════════════════════════════════════════
// OPTIONAL CHAINING & NULLISH COALESCING
// ══════════════════════════════════════════════════════════════
const config = {
    database: {
        host: 'localhost',
        port: 5432,
        credentials: {
            username: 'admin',
            password: null
        }
    }
};

const dbHost = config?.database?.host ?? 'default-host';
const dbPassword = config?.database?.credentials?.password ?? 'default-pass';
const missingProp = config?.nonexistent?.deep?.prop ?? 'fallback';
const methodResult = config?.database?.connect?.() ?? 'not connected';

// ══════════════════════════════════════════════════════════════
// TYPED ARRAYS & ARRAYBUFFER
// ══════════════════════════════════════════════════════════════
const buffer = new ArrayBuffer(16);
const int32View = new Int32Array(buffer);
const float64View = new Float64Array(buffer);
const uint8View = new Uint8Array([72, 101, 108, 108, 111]);
const decoder = new TextDecoder('utf-8');
const decodedText = decoder.decode(uint8View);

// ══════════════════════════════════════════════════════════════
// MAIN / IIFE / TOP-LEVEL
// ══════════════════════════════════════════════════════════════
(async () => {
    console.log('='.repeat(60));
    console.log('JavaScript Syntax Highlighting Test');
    console.log('='.repeat(60));

    const bus = EventBus.create({ name: 'main', debug: true });
    bus.on('test', (msg) => console.log(`Event: ${msg}`));
    bus.emit('test', 'Hello from EventBus');

    const dog = new SerializableDog('Rex', 'German Shepherd');
    console.log(dog.speak());
    console.log(dog.fetch('ball'));

    const counter = createCounter(10);
    counter.increment();
    counter.increment();
    console.log(`Counter: ${counter.value}`);

    const addTen = curry(add)(10);
    console.log(`addTen(5) = ${addTen(5)}`);

    const transform = pipe(
        x => x * 2,
        x => x + 1,
        x => x.toString(),
        x => `Result: ${x}`
    );
    console.log(transform(5));

    console.log('All JavaScript tests passed!');
})();
