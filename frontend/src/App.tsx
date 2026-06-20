import React, { useState, useEffect } from 'react';
import Layout from './components/Layout';

// 页面组件
import Dashboard from './pages/Dashboard';
import ConceptList from './pages/ConceptList';
import ConceptGraph from './pages/ConceptGraph';
import Evolution from './pages/Evolution';
import CrossTheory from './pages/CrossTheory';
import ArticleBrowser from './pages/ArticleBrowser';
import RelationList from './pages/RelationList';
import Synonyms from './pages/Synonyms';
import Settings from './pages/Settings';

console.log('[App.tsx] 模块已加载（含 Layout + 自定义路由）');

// 自定义 Hash 路由器
const useHashRouter = () => {
  const [hash, setHash] = useState(window.location.hash || '#/dashboard');
  
  useEffect(() => {
    const onHashChange = () => {
      setHash(window.location.hash || '#/dashboard');
    };
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);
  
  return hash;
};

// 路由映射
const routes: Record<string, React.ReactNode> = {
  '#/dashboard': <Dashboard />,
  '#/concepts': <ConceptList />,
  '#/concept-graph': <ConceptGraph />,
  '#/evolution': <Evolution />,
  '#/cross-theory': <CrossTheory />,
  '#/articles': <ArticleBrowser />,
  '#/relations': <RelationList />,
  '#/synonyms': <Synonyms />,
  '#/settings': <Settings />,
};

const App: React.FC = () => {
  const hash = useHashRouter();
  
  console.log('[App.tsx] App 渲染中... hash:', hash);
  
  const page = routes[hash] || routes['#/dashboard'];
  
  return (
    <Layout>
      {page}
    </Layout>
  );
};

export default App;
