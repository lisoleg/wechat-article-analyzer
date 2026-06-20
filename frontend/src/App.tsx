import React, { useState, useEffect } from 'react';
import Layout from './components/Layout';

// 页面组件
import Dashboard from './pages/Dashboard';
import ConceptList from './pages/ConceptList';
import ConceptGraph from './pages/ConceptGraph';
import Evolution from './pages/Evolution';
import CrossTheory from './pages/CrossTheory';
import ArticleBrowser from './pages/ArticleBrowser';
import ArticleDetail from './pages/ArticleDetail';
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

// 根据 hash 解析当前页面
const resolvePage = (hash: string): React.ReactNode => {
  // 精确匹配
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
  if (routes[hash]) return routes[hash];

  // 动态路由：#/articles/:id
  if (hash.startsWith('#/articles/')) {
    const id = hash.replace('#/articles/', '');
    if (id) return <ArticleDetail id={id} />;
  }

  // 未匹配：回到仪表盘
  return <Dashboard />;
};

const App: React.FC = () => {
  const hash = useHashRouter();
  
  console.log('[App.tsx] App 渲染中... hash:', hash);
  
  const page = resolvePage(hash);
  
  return (
    <Layout>
      {page}
    </Layout>
  );
};

export default App;
