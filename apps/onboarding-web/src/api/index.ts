import { DatabricksMockAPI } from './mock'
import { DatabricksRealAPI } from './databricks'
import type { DatabricksAPI } from './interface'

// Change to 'real' when ready to connect to live Databricks workspace
const API_MODE = (import.meta.env.VITE_API_MODE || 'mock') as 'mock' | 'real'

export const api: DatabricksAPI = API_MODE === 'real' ? DatabricksRealAPI : DatabricksMockAPI

export type { DatabricksAPI }
export type { WorkspaceValidationResult, DocumentProcessingResult } from '../types'
