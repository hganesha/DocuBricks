import React, { Suspense } from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'

const WelcomeScreen = React.lazy(() => import('./screens/WelcomeScreen'))
const ProjectScreen = React.lazy(() => import('./screens/ProjectScreen'))
const VerticalScreen = React.lazy(() => import('./screens/VerticalScreen'))
const WorkspaceScreen = React.lazy(() => import('./screens/WorkspaceScreen'))
const ResourcesScreen = React.lazy(() => import('./screens/ResourcesScreen'))
const ReviewScreen = React.lazy(() => import('./screens/ReviewScreen'))
const DeployingScreen = React.lazy(() => import('./screens/DeployingScreen'))
const FirstDocScreen = React.lazy(() => import('./screens/FirstDocScreen'))

function PageFallback() {
  return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <div className="w-5 h-5 rounded-full bg-accent-700 animate-pulse" />
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<PageFallback />}>
        <Routes>
          <Route path="/" element={<WelcomeScreen />} />
          <Route path="/project" element={<ProjectScreen />} />
          <Route path="/vertical" element={<VerticalScreen />} />
          <Route path="/workspace" element={<WorkspaceScreen />} />
          <Route path="/resources" element={<ResourcesScreen />} />
          <Route path="/review" element={<ReviewScreen />} />
          <Route path="/deploying" element={<DeployingScreen />} />
          <Route path="/first-doc" element={<FirstDocScreen />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  )
}
