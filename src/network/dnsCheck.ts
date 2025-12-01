/**
 * Module de vérification DNS
 * Vérifie si un domaine existe et est résolvable
 * Supporte DNS lookup et CNAME resolution
 */

import { lookup, resolveCname as dnsResolveCname } from 'dns/promises';

export interface DnsCheckResult {
  ok: boolean;
  address?: string;
  error?: string;
}

export interface DnsLookupResult {
  ok: boolean;
  address?: string;
  family?: number;
  error?: string;
}

export interface CnameResult {
  ok: boolean;
  cnames: string[];
  error?: string;
}

/**
 * Vérifie si un domaine existe via DNS (alias pour compatibilité)
 * @param domain - Le domaine à vérifier (ex: "example.com")
 * @returns Résultat de la vérification DNS
 */
export async function dnsCheck(domain: string): Promise<DnsCheckResult> {
  const result = await dnsLookup(domain);
  return {
    ok: result.ok,
    address: result.address,
    error: result.error,
  };
}

/**
 * Effectue un DNS lookup pour un domaine
 * @param domain - Le domaine à résoudre
 * @returns Résultat du lookup avec adresse IP et famille
 */
export async function dnsLookup(domain: string): Promise<DnsLookupResult> {
  try {
    const addresses = await lookup(domain, {
      family: 4, // IPv4
      all: false,
    });

    return {
      ok: true,
      address: addresses.address,
      family: addresses.family,
    };
  } catch (error: any) {
    return {
      ok: false,
      error: error.message || 'DNS lookup failed',
    };
  }
}

/**
 * Résout les enregistrements CNAME pour un domaine
 * @param domain - Le domaine à résoudre
 * @returns Résultat avec liste des CNAMEs
 */
export async function resolveCname(domain: string): Promise<CnameResult> {
  try {
    const cnames = await dnsResolveCname(domain);
    return {
      ok: true,
      cnames: cnames,
    };
  } catch (error: any) {
    // CNAME peut ne pas exister, ce n'est pas forcément une erreur
    if (error.code === 'ENODATA' || error.code === 'ENOTFOUND') {
      return {
        ok: false,
        cnames: [],
      };
    }
    return {
      ok: false,
      cnames: [],
      error: error.message || 'CNAME resolution failed',
    };
  }
}

